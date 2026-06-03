# Audit ActivityPub — Suddenly (federation complète)

- **Date** : 2026-05-29
- **Stack** : Django 5.0 + `httpx` + `cryptography` + Celery + Redis
- **Pattern AP** : implémentation custom (pas de librairie AP tierce)
- **Scope** : federation complète — inbox, delivery, conformance, sécurité, observabilité
- **Source checklist** : schéma générique §1–§11 + `references/ap-protocol-specs.md` (aucun pivot `ap-pivots-django-activitypub.md` installé)

---

## ⚠️ Découverte critique — Deux inbox, le mauvais est routé

Le projet contient **deux implémentations d'inbox concurrentes** :

| Fichier | Sécurité | Routé ? |
|---------|----------|---------|
| `inbox.py` | ✅ signature + idempotence + rate limit + validation domaine acteur | ❌ **JAMAIS importé** (`grep` import = 0 résultat) |
| `views.py` (`user_inbox`, `game_inbox`, `character_inbox`) | ❌ `# TODO: Verify HTTP signature` / `# TODO: Process incoming activity` | ✅ **routé par `urls.py`** |

`urls.py:12,17,21` pointe vers `views.user_inbox` / `views.game_inbox` / `views.character_inbox` — les vues **non sécurisées**. Tout le durcissement de `inbox.py` (vérification de signature, déduplication atomique, rate limiting par instance, validation acteur↔signature) est du **code mort**.

**Conséquence** : en l'état, n'importe qui peut POSTer une activité non signée à `/users/<x>/inbox` et déclencher un `Follow`, `Create(Character)`, `Delete`, etc. via `process_incoming_activity.delay()`. C'est une **faille d'usurpation et de spoofing d'acteur non authentifié**.

> Ceci invalide les tests `test_inbox_*` : ils testent `inbox.process_inbox` (sécurisé) alors que la production sert `views.user_inbox` (non sécurisé). Faux sentiment de couverture.

---

## Baseline

Mesure DB non capturée (pas d'accès shell prod dans cette session). Commandes persistées dans `baselines/full-federation.json`. Observations statiques :

| Métrique | Valeur statique observée |
|----------|--------------------------|
| Garde idempotence active en prod | 🔴 non (route → `views.py`) |
| Vérification signature active en prod | 🔴 non (route → `views.py`) |
| Rate limiting actif en prod | 🔴 non (route → `views.py`) |
| Circuit breaker par domaine | 🔴 absent |
| Garde SSRF sur fetch acteur | 🔴 absent |
| Pagination outbox conforme | 🔴 non (`OrderedCollection` inline, pas de `first`/page) |
| Métriques delivery/inbox | 🔴 logs seulement, pas de compteurs |

---

## Checklist §1–§11

### §1 — Idempotence inbox

| Item | Statut | Référence |
|------|--------|-----------|
| Garde de déduplication présente | 🟡 | `inbox.py:145-161` — **mais non routé** |
| Race-safe (`get_or_create` + contrainte unique) | 🟢 | `models.py:118` `ap_id unique=True` + `IntegrityError` catch `inbox.py:159` |
| Effective en production | 🔴 | `views.py` (routé) appelle `process_incoming_activity.delay()` sans dédup |

**Constat** : `tasks.handle_undo` dédup via `Follow.ap_id`, mais aucun garde `ProcessedActivity` dans le chemin réel. Replay possible.

### §2 — Vérification de signature

| Item | Statut | Référence |
|------|--------|-----------|
| Présente + headers vérifiés | 🟡 | `signatures.py:223` — **non routé** |
| Vérif Digest vs body | 🟢 | `signatures.py:260-266` (dans `inbox.py` mort) |
| Date skew / fenêtre temporelle | 🔴 | aucune vérif de `Date` ni anti-replay temporel |
| Vérif **avant** parse du payload | 🟡 | `inbox.py:104` ok, mais `views.py:229` parse sans vérif |
| Effective en production | 🔴 | `views.py:226` `# TODO: Verify HTTP signature` |

**Manque spec** : HTTP Signatures (draft-cavage §2.1) recommande de rejeter les requêtes dont l'en-tête `Date` dévie de >30s (anti-replay). Absent partout, même dans `inbox.py`.

### §3 — Fan-out delivery

| Item | Statut | Référence |
|------|--------|-----------|
| Asynchrone (Celery) | 🟢 | `tasks.py:187` `deliver_activity` shared_task |
| `transaction.on_commit` | 🔴 | `signals.py` appelle `_safe_delay()` direct — risque d'envoi avant commit DB |
| Une tâche par destinataire | 🟢 | `tasks.py:272-275` boucle `deliver_activity.delay` par inbox |
| Retry backoff | 🟡 | `tasks.py:229,232` retry linéaire `60*(retries+1)`, pas exponentiel ; `max_retries=3` |

**Manque** : `signals.py:49,69,81` déclenchent `_safe_delay` dans `post_save` sans `transaction.on_commit`. Si la transaction rollback après le `post_save`, l'activité est déjà partie. Pattern requis (cf. `data-pivots-django-orm.md §9`).

### §4 — Cache acteur / clés

| Item | Statut | Référence |
|------|--------|-----------|
| Clé publique cachée | 🟢 | `PublicKeyCache` DB (`models.py:77`, DEC-020) |
| TTL / invalidation | 🟡 | re-fetch uniquement si vérif échoue (`signatures.py:277`) ; pas de TTL proactif, jamais invalidé sur `Update Person` |
| Cache du document acteur | 🔴 | `get_or_create_remote_user` (×2, `inbox.py:552` + `tasks.py:612`) fetch HTTP sans cache hors DB |

**Manque** : sur réception d'un `Update(Person)` distant, la clé en cache n'est pas invalidée — rotation de clé non prise en compte tant que la vérif ne casse pas.

### §5 — Pagination outbox

| Item | Statut | Référence |
|------|--------|-----------|
| `OrderedCollection` avec `first` | 🔴 | `views.py:261-269` renvoie `orderedItems` inline tronqué `[:20]` |
| `OrderedCollectionPage` (`partOf`/`next`/`prev`) | 🔴 | absent — pas de pagination réelle |
| `totalItems` correct | 🟡 | `reports.count()` ok mais items plafonnés à 20 sans page suivante |

S'applique aux 3 outbox (user `views.py:243`, game `:344`, character `:409`) et aux `followers` (`:273`). Non conforme W3C AP §5.1.

### §6 — Rate limiting

| Item | Statut | Référence |
|------|--------|-----------|
| Inbox rate-limité par host | 🟡 | `inbox.py:37-57` (DEC-021) — **non routé** |
| Retourne 429 + `Retry-After` | 🔴 | `inbox.py:101` renvoie **403** (devrait être 429 + `Retry-After`) |
| Effective en production | 🔴 | `views.py` sans rate limit |

### §7 — Circuit breaker

| Item | Statut | Référence |
|------|--------|-----------|
| Compteur d'échec par domaine | 🔴 | absent |
| Mode backoff après N échecs | 🔴 | retry par activité seulement, pas de coupe-circuit instance |
| `410 Gone` → suppression locale | 🔴 | `deliver_activity` ne gère pas 410 ; 4xx ≠ 5xx non distingués (`tasks.py:228` ne retry que ≥500, mais ne supprime rien sur 410) |

`FederatedServer.status=BLOCKED` existe (`models.py:18`) mais n'est jamais consulté avant delivery — aucun usage du statut comme coupe-circuit.

### §8 — Conformance AS2

| Item | Statut | Référence |
|------|--------|-----------|
| `@context` sur objets sortants | 🟢 | `serializers.py:14` `AP_CONTEXT` + `https://w3id.org/security/v1` |
| `id` URL absolue | 🟢 | partout |
| Namespace custom `suddenly:` | 🟡 | `serializers.py:18` utilise `settings.DOMAIN` dynamique — **viole** la règle "URL namespace stable" (`08-activitypub.md`) : doit être `https://suddenly.social/ns#` figé, pas dépendant du domaine d'instance |
| Content-Type d'envoi | 🔴 | `tasks.py:208` envoie `application/activity+json` ; la règle exige `application/ld+json; profile="..."` à l'inbox |
| Filtrage activités Suddenly-only | 🔴 | `serialize_link_request` (Offer Claim/Adopt/Fork) jamais filtré par `is_suddenly_instance()` avant envoi — viole `08-activitypub.md` |

**Manque conformité** : le namespace `suddenly:` change selon `soudainement.fr` vs `suddenly.social` → deux instances Suddenly ne s'interprètent pas. Bug de federation silencieux.

### §9 — Sécurité

| Item | Statut | Référence |
|------|--------|-----------|
| Garde SSRF sur URL acteur | 🔴 | `get_or_create_remote_user` / `_fetch_public_key` fetch toute URL sans bloquer `localhost`/`127.0.0.1`/`169.254`/IP privées |
| Acteur correspond au keyId de signature | 🟢 | `inbox.py:127-143` — **non routé** ; absent en prod |
| Requêtes sortantes signées | 🟢 | `tasks.py:213` signe si clé fournie |
| Fallback non signé | 🟡 | `tasks.py:213` envoie non signé si pas de clé (acceptable en dev, risqué en prod) |

**SSRF (critique)** : `_fetch_public_key` (`signatures.py:162`) et les deux `get_or_create_remote_user` suivent l'URL `keyId`/`actor` fournie par l'attaquant. Sans allowlist de schéma/host ni blocage des IP privées, un attaquant peut faire scanner le réseau interne par le serveur (OWASP SSRF). Aggravé par §2 : aucune signature requise pour atteindre ce code.

### §10 — Observabilité

| Item | Statut | Référence |
|------|--------|-----------|
| Événements inbox loggés | 🟡 | `logger.info` épars ; pas de log structuré |
| Événements delivery loggés | 🔴 | `deliver_activity` ne logge **ni succès ni échec** (`tasks.py:225-232`) |
| Compteurs métriques | 🔴 | aucun (`ap:delivered:ok/fail` mentionnés dans le skill n'existent pas) |
| Alerting | 🔴 | absent |

### §11 — Vérification (tests)

| Item | Statut | Référence |
|------|--------|-----------|
| Test idempotence | 🟡 | `test_activitypub.py` teste `inbox.process_inbox` (code mort) |
| Test SSRF | 🔴 | absent |
| Test replay | 🟡 | teste le mauvais chemin |
| Test retry delivery | 🟡 | `test_security.py` existe, couverture delivery à confirmer |
| **Tests testent le code réellement routé** | 🔴 | **non** — gap majeur : `views.py` inbox non testé |

---

## Roadmap

### F0 — Sécurité (à livrer immédiatement)

1. **Router l'inbox sécurisé** — faire pointer `urls.py` vers `inbox.user_inbox/game_inbox/character_inbox` (ou fusionner `inbox.py` dans `views.py` et supprimer les vues `# TODO`). Supprimer le code mort.
   - *Effort* : M · *Risque* : élevé si mal fait (régression federation) · *Spec* : W3C AP §7.1.1 (inbox MUST verify)
   - *Critère* : POST non signé → 403 ; `ProcessedActivity.count()` augmente sur activité valide
2. **Garde SSRF** sur tout fetch sortant (`_fetch_public_key`, les 2 `get_or_create_remote_user`, `fetch_remote_actor`) — allowlist `https` + blocage IP privées/loopback/link-local avant `httpx.get`.
   - *Effort* : S · *Risque* : faible · *Spec* : OWASP SSRF
   - *Critère* : test `https://127.0.0.1/` → refus
3. **Date skew anti-replay** — rejeter signatures dont `Date` dévie de >30s.
   - *Effort* : S · *Spec* : draft-cavage §2.1

### F1 — Fiabilité

4. `transaction.on_commit` autour de tous les `_safe_delay` dans `signals.py` — éviter l'envoi avant commit.
   - *Effort* : S · *Spec* : Django on_commit
5. **Circuit breaker par domaine** — consulter `FederatedServer.status` avant delivery ; compteur d'échec → `BLOCKED` après N ; gérer `410 Gone` → suppression locale de l'acteur.
   - *Effort* : M · *Critère* : queue depth ne gonfle pas sur instance morte
6. **Retry exponentiel** — `countdown=2**retries` au lieu de linéaire (`tasks.py:229,232`).
   - *Effort* : S

### F2 — Conformance

7. **Figer le namespace** `suddenly:` à `https://suddenly.social/ns#` (constante, indépendante de `settings.DOMAIN`).
   - *Effort* : S · *Risque* : breaking si déjà fédéré · *Spec* : `08-activitypub.md`
8. **Content-Type d'envoi** → `application/ld+json; profile="https://www.w3.org/ns/activitystreams"` (`tasks.py:208`).
   - *Effort* : XS
9. **Pagination outbox** — `OrderedCollection` + `first` → `OrderedCollectionPage` (`partOf`/`next`/`prev`) sur les 4 collections.
   - *Effort* : M · *Spec* : W3C AP §5.1
10. **Filtrer les Offer Suddenly-only** — ne pas envoyer Claim/Adopt/Fork aux instances non-Suddenly (`is_suddenly_instance()`).
    - *Effort* : S · *Spec* : `08-activitypub.md`

### F3 — Observabilité / Performance

11. Logger succès/échec de `deliver_activity` + compteurs (`ap:delivered:ok/fail`, `ap:inbox:received/dup/rejected`).
12. Invalidation `PublicKeyCache` sur `Update(Person)` + TTL proactif.
13. 429 + `Retry-After` au lieu de 403 sur rate limit (`inbox.py:101`).

---

## Quick wins (≤ 4, priorité sécurité)

1. **Router `inbox.py` à la place de `views.py`** (F0-1) — neutralise à lui seul les failles §1, §2, §6, §9-acteur. *Le fix le plus rentable de l'audit.*
2. **Garde SSRF** (F0-2) — ~20 lignes, bloque le scan réseau interne.
3. **Content-Type `ld+json` à l'envoi** (F2-8) — 1 ligne, conformité immédiate.
4. **`transaction.on_commit`** dans `signals.py` (F1-4) — évite les envois fantômes sur rollback.

---

## Checklist learnings

- `[antipattern] Deux implémentations parallèles d'un endpoint critique (inbox.py sécurisé / views.py TODO) avec routage vers la non-sécurisée | masque la faille ET fausse la couverture de tests — symptôme transverse à élever`
- `[gap] §2 : aucune vérification de Date skew / fenêtre anti-replay temporel — absente même dans le code sécurisé`
- `[gap] §9 : pas de section dédiée SSRF allowlist dans le schéma générique — le fetch d'acteur attaquant-contrôlé est un vecteur AP classique non couvert`
- `[gap] §11 : la checklist ne vérifie pas que les tests couvrent le code RÉELLEMENT routé (vs code mort) — gap méthodologique`
- `[spec] §8 : namespace JSON-LD custom dépendant de settings.DOMAIN casse la federation inter-instances Suddenly (soudainement.fr ↔ suddenly.social)`
- `[grep] grep -rn "from .inbox\|import inbox" — surface le code mort : un module de sécurité jamais importé`
- `[fp] §3 retry : max_retries=3 présent — non-conforme backoff exponentiel mais pas absent, donc 🟡 pas 🔴`

> Seuil de déclenchement atteint (≥ 2 gaps + 1 antipattern + pivot manquant). **Proposition** : générer `.claude/rules/07-quality/ap-pivots-django-activitypub.md` à partir de cet audit, et ajouter au schéma générique `ap-protocol-specs.md` les sections "Date skew anti-replay" (§2) et "SSRF allowlist sur fetch acteur" (§9). À valider avec toi avant application.
