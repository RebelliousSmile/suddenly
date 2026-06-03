# Audit ActivityPub — Suddenly (full-federation v2)

- **Date** : 2026-05-29
- **Stack** : Django 5.0 + `httpx` + `cryptography` + Celery + Redis
- **Pattern AP** : implémentation custom (pas de librairie AP tierce)
- **Pivot source** : `.claude/rules/07-quality/ap-pivots-django-activitypub.md`
- **Scope** : full-federation — inbox, delivery, signatures, outbox, sécurité, observabilité
- **Fichiers lus** : `activitypub/inbox.py`, `activitypub/views.py`, `activitypub/signatures.py`, `activitypub/tasks.py`, `activitypub/activities.py`, `activitypub/serializers.py`, `activitypub/models.py`, `activitypub/urls.py`

---

## Baseline

Mesures statiques dérivées de l'analyse du code source (accès shell non disponible).

| Signal | Valeur | Source |
|--------|--------|--------|
| Signature verification active | ❌ NON | `views.py:226` — `# TODO` |
| Idempotency guard actif | ❌ NON | `urls.py` → `views.py` (pas `inbox.py`) |
| Rate limiting actif | ❌ NON | `views.py` — aucun appel ratelimit |
| Circuit breaker | ❌ NON | `tasks.py` — pas de compteur domaine |
| SSRF guard | ❌ NON | 3 points non protégés |
| Métriques AP | ❌ NON | aucun counter Redis/log structuré |
| Pagination outbox conforme | ❌ NON | inline `orderedItems` sans page |

Commandes pour les valeurs runtime :
```bash
python manage.py shell -c "from suddenly.activitypub.models import ProcessedActivity; print(ProcessedActivity.objects.count())"
redis-cli LLEN celery
```

---

## Découverte critique — Dead code vs endpoints actifs

**La `urls.py` active câble `views.py` pour tous les inboxes, pas `inbox.py`.**

```
activitypub/urls.py:
  path("users/<str:username>/inbox", views.user_inbox, ...)   ← views.py
  path("games/<uuid:game_id>/inbox", views.game_inbox, ...)   ← views.py
  path("characters/<uuid:character_id>/inbox", ...)            ← views.py
```

`inbox.py` contient une implémentation complète (signature, rate limit, idempotency, actor domain check) mais **n'est jamais appelée** — c'est du code mort. `views.py` est l'endpoint live et n'a aucun de ces contrôles.

Cette divergence explique la plupart des 🔴 ci-dessous.

---

## Checklist §1–§11

### §1 — Inbox idempotency

| Item | Statut | Référence |
|------|--------|-----------|
| Guard `ProcessedActivity` avant traitement | 🔴 | `views.py:215–238` — absent |
| Race-safe (`get_or_create` + `IntegrityError`) | 🟡 | `inbox.py:145–161` — implémenté mais mort |
| Contrainte unique sur `ap_id` | 🟢 | `models.py:118` — `unique=True` présent |
| Retour 202 sur doublon | 🔴 | `views.py` — retourne 202 sans vérification |

**Verdict : 🔴 MISSING**
Les endpoints actifs ne vérifient pas `ProcessedActivity`. Un acteur malveillant peut rejouer la même activité indéfiniment et déclencher plusieurs fois le même handler.

Spec : W3C AP §7.2.1 — "The server SHOULD verify that the object linked in the message is current."

---

### §2 — Signature HTTP (vérification)

| Item | Statut | Référence |
|------|--------|-----------|
| Vérification appelée avant parse | 🔴 | `views.py:226` — commentaire `# TODO` |
| Algorithm check (`rsa-sha256`) | 🟢 | `signatures.py:256` |
| Digest header vérifié | 🟡 | `signatures.py:261` — seulement si présent, pas obligatoire |
| Date skew (±30s) | 🔴 | `signatures.py` — absent de `verify_signature` |
| Headers signés obligatoires | 🟢 | `signatures.py` — `(request-target) host date digest` |
| Cache clé avec re-fetch | 🟢 | `signatures.py:272–284` |

**Verdict : 🔴 MISSING**
`views.py:user_inbox` ligne 226 : `# TODO: Verify HTTP signature`. N'importe qui peut envoyer une activité sans signature. `signatures.py` est bien implémenté mais jamais appelé depuis les endpoints actifs.

Spec : HTTP Signatures draft-cavage §2.5 — Verification REQUIRED on all POST requests.

---

### §3 — Fan-out delivery (livraison sortante)

| Item | Statut | Référence |
|------|--------|-----------|
| Livraison via Celery task | 🟢 | `tasks.py:187` — `deliver_activity` |
| `transaction.on_commit` avant `.delay()` | 🔴 | `inbox.py:257`, `tasks.py:109` — absent partout |
| Une task par destinataire | 🟢 | `tasks.py:broadcast_activity:272–274` |
| Retry backoff exponentiel | 🟡 | `tasks.py:229` — `countdown=60 * (retries+1)` linéaire, pas exponentiel |
| Accept signé dans `send_accept_follow` | 🔴 | `tasks.py:305` — `deliver_activity.delay(accept, inbox_url)` sans clés |
| `max_retries` défini | 🟢 | `tasks.py:22,186` — `max_retries=3` |

**Verdict : 🟡 PARTIAL**
- `transaction.on_commit` absent : une task peut partir avant que la FK soit committée en DB → `DoesNotExist` possible à l'exécution.
- `send_accept_follow` (tasks.py:305) délivre sans signer : les instances distantes rejetteront probablement les Accept non signés.
- Retry linéaire au lieu d'exponentiel : risque de flood sur instances down.

Spec : W3C AP §6.1 — Delivery MUST be async; on_commit garantit la cohérence.

---

### §4 — Actor fetching & key caching

| Item | Statut | Référence |
|------|--------|-----------|
| Clé en cache (`PublicKeyCache`) | 🟢 | `signatures.py:272` |
| Fetch uniquement sur miss | 🟢 | `signatures.py:287` |
| Re-fetch sur échec vérification | 🟢 | `signatures.py:279` |
| TTL sur le cache (expiry) | 🔴 | `models.py:93` — `fetched_at` présent mais aucune expiry logique |
| Invalidation sur `Update Person` | 🔴 | Absent — aucun handler Update ne clear le cache |
| SSRF guard avant fetch acteur | 🔴 | `signatures.py:162`, `inbox.py:573`, `tasks.py:625` — 3 points non protégés |

**Verdict : 🟡 PARTIAL**
Cache fonctionnel mais sans TTL : une clé compromise reste en cache indéfiniment. `Update Person` distant n'invalide pas le cache local.

---

### §5 — Outbox pagination (conformité AP)

| Item | Statut | Référence |
|------|--------|-----------|
| `OrderedCollection` avec `first` pointer | 🔴 | `views.py:262,354,420` — `orderedItems` inline |
| `OrderedCollectionPage` avec `partOf`/`next`/`prev` | 🔴 | Absent |
| Taille de page bornée | 🟡 | `[:20]` hardcodé mais pas de cursor |
| `Accept: application/activity+json` supporté | 🟢 | `views.py:44` — content negotiation |
| `totalItems` présent | 🟢 | présent dans les trois outboxes |

**Verdict : 🔴 MISSING**
Les trois outboxes (user, game, character) retournent des `OrderedCollection` avec `orderedItems` inline — format non conforme AP. Mastodon et Misskey attendent `first` → `OrderedCollectionPage`. Sans pagination correcte, les instances distantes ne peuvent pas traverser l'historique.

Spec : W3C AP §5.1 — Collection MUST have `first` if `totalItems > 0`; each page needs `partOf`, `next`.

---

### §6 — Rate limiting inbox

| Item | Statut | Référence |
|------|--------|-----------|
| Rate limit par IP sur inbox POST | 🔴 | `views.py` — absent |
| Rate limit par domaine distant | 🟡 | `inbox.py:37–57` — implémenté mais mort |
| Retour 429 avec `Retry-After` | 🔴 | `inbox.py:101` retourne 403, pas 429 |
| Connexes connus plus permissifs | 🟢 | `inbox.py:23` — 100/min vs 10/min |

**Verdict : 🔴 MISSING**
Aucun rate limiting sur les endpoints actifs. Une instance hostile peut flood l'inbox sans frein.

Spec : HTTP §6.5.29 — 429 REQUIRED avec Retry-After pour signaler le throttle.

---

### §7 — Instance health & circuit breaker

| Item | Statut | Référence |
|------|--------|-----------|
| Compteur d'échecs par domaine | 🔴 | Absent |
| Circuit breaker après N échecs | 🔴 | Absent |
| `4xx` = erreur permanente (pas de retry) | 🔴 | `tasks.py:228` — seul `>=500` retry ; 4xx ignorés silencieusement |
| `410 Gone` → suppression locale | 🔴 | Absent |
| Logging échec livraison | 🟡 | `tasks.py:232` — exception loggée via `raise self.retry` seulement |

**Verdict : 🔴 MISSING**
`deliver_activity` ignore silencieusement les 4xx (y compris 410 Gone). Un acteur supprimé reste en DB et génère des tentatives de livraison infinies jusqu'à `max_retries`.

---

### §8 — Conformité AS2 (types d'objets)

| Item | Statut | Référence |
|------|--------|-----------|
| `@context` sur toutes les activités sortantes | 🟢 | `serializers.py:14` — `AP_CONTEXT` systématique |
| `id` absolu sur toutes les activités | 🟡 | `activities.py:254,268` — `Follow`/`Undo` utilisent `timezone.now().timestamp()` comme `id` → instable |
| `type` présent | 🟢 | Présent partout |
| Namespace `suddenly` dans `@context` | 🟢 | `serializers.py:17` — namespace déclaré |
| Namespace stable (non-dynamique) | 🟡 | `f"https://{settings.DOMAIN}/ns#"` — stable si DOMAIN fixe |
| `id` manquant sur `Create` via `create_activity()` | 🔴 | `serializers.py:269–286` — `create_activity()` n'ajoute pas `id` |
| Types supportés : Create, Update, Delete, Follow, Accept, Reject, Undo, Offer | 🟢 | Tous gérés |

**Verdict : 🟡 PARTIAL**
- `create_activity()` (serializers.py:269) ne génère pas d'`id` → les activités Create sortantes n'ont pas d'identifiant stable.
- `build_follow_activity` et `build_undo_activity` dans `activities.py` utilisent `timezone.now().timestamp()` comme `id` → non-déterministes, impossible à référencer.

Spec : W3C AS2 §4.1 — `id` MUST be an absolute IRI; W3C AP §6 — Activities MUST have `id`.

---

### §9 — Sécurité

| Item | Statut | Référence |
|------|--------|-----------|
| SSRF guard avant fetch acteur | 🔴 | `inbox.py:573`, `signatures.py:162`, `tasks.py:625` |
| `actor` validé vs signature keyId | 🔴 | `views.py:user_inbox` — pas de vérification signature → pas de validation actor |
| Requêtes sortantes signées | 🟡 | `tasks.py:213` — signé si `actor_key_id` fourni ; `send_accept_follow:305` non signé |
| Rotation de clé + invalidation cache | 🔴 | Absent |

**Verdict : 🔴 MISSING**

**SSRF critique** : trois fonctions fetchent une URL distante sans validation préalable :
- `inbox.py:get_or_create_remote_user:573` — `httpx.Client().get(actor_url)`
- `signatures.py:_fetch_public_key:162` — `httpx.Client().get(actor_url)`
- `tasks.py:get_or_create_remote_user:625` — `httpx.Client().get(actor_url)`

Un acteur distant peut envoyer `"actor": "http://localhost/admin/"` → Suddenly fetchera l'URL interne.

Fix immédiat :
```python
from urllib.parse import urlparse

def _is_ssrf_target(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    return host in ("localhost", "127.0.0.1", "::1") or host.startswith("169.254")
```

Spec : OWASP SSRF — validation obligatoire avant tout fetch d'URL fournie par une source distante.

---

### §10 — Observabilité

| Item | Statut | Référence |
|------|--------|-----------|
| Inbox events loggés (activity_id, type, actor) | 🔴 | `views.py` — aucun log structuré |
| Delivery events loggés (target_inbox, status_code, duration_ms) | 🔴 | `tasks.py:deliver_activity` — aucun log de succès |
| Métriques Redis (`ap:delivered:ok`, etc.) | 🔴 | Absent |
| Alerte si queue Celery dépasse seuil | 🔴 | Absent |
| Logging échec structuré | 🟡 | `tasks.py:54` — `logger.exception()` présent dans `process_incoming_activity` |

**Verdict : 🔴 MISSING**
`deliver_activity` ne logue rien sur succès (status 2xx). Impossible de calculer le taux de succès de livraison.

---

### §11 — Vérification

| Item | Statut | Référence |
|------|--------|-----------|
| Test idempotence (double POST → 1 traitement) | 🔴 | `coverage.omit` inclut `inbox.py` |
| Test SSRF (`http://localhost/` → exception) | 🔴 | Non trouvé |
| Test replay (activité identique → 202 sans retraitement) | 🔴 | Non trouvé |
| Test delivery retry | 🟡 | Non trouvé (coverage.omit inclut `tasks.py`) |

**Verdict : 🔴 MISSING**
`pyproject.toml:111–116` exclut `activitypub/inbox.py`, `activitypub/tasks.py`, et `activitypub/activities.py` de la couverture — les chemins AP critiques sont non testés.

---

## Score de conformité

| Phase | Items | 🟢 | 🟡 | 🔴 |
|-------|-------|----|----|-----|
| F0 Sécurité | 8 | 0 | 1 | 7 |
| F1 Fiabilité | 7 | 3 | 3 | 1 |
| F2 Conformité | 7 | 4 | 2 | 1 |
| F3 Performance | 4 | 0 | 0 | 4 |
| **Total** | **26** | **7** | **6** | **13** |

---

## Roadmap

### F0 — Sécurité (shipper immédiatement)

**F0-1 : Brancher `inbox.py` à la place de `views.py` pour les inboxes** ⚠️ CRITIQUE
- Modifier `activitypub/urls.py` pour pointer sur `inbox.user_inbox`, `inbox.game_inbox`, `inbox.character_inbox`
- OU porter la logique de `inbox.py:process_inbox` dans `views.py`
- Effort : 1h | Risque : aucun rollback nécessaire — inbox.py est complet
- Critère : toute POST /inbox sans signature valide retourne 403

**F0-2 : SSRF guard sur les 3 points de fetch** ⚠️ CRITIQUE
- Ajouter `_is_ssrf_target(url)` avant tout `httpx.get(actor_url)` dans :
  - `inbox.py:573`
  - `signatures.py:162`
  - `tasks.py:625`
- Effort : 2h | Risque : faible (validation d'entrée uniquement)
- Critère : `pytest` avec `actor_url="http://localhost/"` → ValueError avant tout fetch

**F0-3 : Date skew check dans `verify_signature`**
- Ajouter validation `Date` header ±30s dans `signatures.py:verify_signature`
- Effort : 1h | Risque : faible
- Spec : HTTP Signatures §2.3

---

### F1 — Fiabilité

**F1-1 : `transaction.on_commit` avant tous les `.delay()`**
- `inbox.py:257`, `tasks.py:109` (send_accept_follow → deliver_activity)
- Pattern : `transaction.on_commit(lambda: deliver_activity.delay(...))`
- Effort : 2h

**F1-2 : Signer les Accept dans `send_accept_follow`**
- `tasks.py:305` — ajouter `actor_key_id` et `private_key_pem` depuis `get_actor_signing_keys(target)`
- Effort : 30min

**F1-3 : Gérer 4xx et 410 dans `deliver_activity`**
```python
if response.status_code == 410:
    # Unfederate l'acteur
    User.objects.filter(inbox_url=inbox_url).update(remote=True, active=False)
    return
if 400 <= response.status_code < 500:
    logger.warning("Permanent delivery failure %s → %s", inbox_url, response.status_code)
    return  # ne pas retry
```
- Effort : 2h

**F1-4 : TTL sur `PublicKeyCache`**
- Ajouter logique d'expiry : re-fetch si `fetched_at < now() - 1h`
- Effort : 1h

---

### F2 — Conformité

**F2-1 : Pagination outbox**
Convertir les trois outboxes en `OrderedCollection` → `OrderedCollectionPage` :
```python
# user_outbox — exemple
return activitypub_response({
    "@context": "https://www.w3.org/ns/activitystreams",
    "type": "OrderedCollection",
    "id": f"{user.actor_url}/outbox",
    "totalItems": count,
    "first": f"{user.actor_url}/outbox?page=1",
})
# GET /outbox?page=1 → OrderedCollectionPage avec partOf, next, orderedItems
```
- Effort : 4h

**F2-2 : `id` sur toutes les activités sortantes**
- `serializers.py:create_activity()` — ajouter génération d'`id` stable basé sur UUID ou timestamp ISO
- `activities.py:build_follow_activity` — remplacer `timezone.now().timestamp()` par un UUID

---

### F3 — Performance

**F3-1 : Circuit breaker par domaine**
- Compteur Redis `ap:fail:<domain>` incrémenté à chaque échec
- Après 5 échecs : skip livraison 24h, logguer `ap:circuit_open:<domain>`

**F3-2 : Logging livraison structuré**
```python
logger.info(
    "AP delivery",
    extra={"inbox": inbox_url, "status": response.status_code, "attempt": self.request.retries}
)
```

---

## Quick wins (≤ 4 items, priorité sécurité)

1. **[F0-1] Brancher `inbox.py`** dans `urls.py` — 1 ligne changée, active immédiatement signature + idempotency + rate limit
2. **[F0-2] SSRF guard** — 10 lignes de validation, 3 points
3. **[F1-2] Signer les Accept** dans `send_accept_follow` — 2 lignes
4. **[F1-3] Gérer 410 Gone** dans `deliver_activity` — arrête les livraisons infinies vers des acteurs supprimés

---

## Checklist learnings

**[gap] §2** : Date skew check absent de `verify_signature` — le pivot ne le liste pas comme tripwire de détection mais c'est un vecteur replay critique distinct du Digest check.

**[gap] §3** : `transaction.on_commit` pas inclus dans les commandes de détection rapide du pivot — ajouter `grep -rn "delay(" activitypub/ | grep -v "on_commit"` comme tripwire.

**[antipattern] Dead code inbox vs active views** : deux implémentations parallèles d'un même endpoint, l'une sécurisée mais non câblée. Cause : développement en branche séparée sans mise à jour de `urls.py`. Motif récurrent : URL routing comme vecteur de régression silencieuse.

**[antipattern] coverage.omit sur chemins AP critiques** : `activitypub/inbox.py`, `activitypub/tasks.py`, `activitypub/activities.py` sont exclus de la couverture dans `pyproject.toml:111–116` — les chemins les plus sensibles ne sont pas testés.

**[spec] §5** : W3C AP §5.1 exige `first` sur toute `OrderedCollection` non-vide — l'implémentation inline `orderedItems` est silencieusement non conforme (pas d'erreur côté client, mais les crawlers AP ne peuvent pas paginer).

**[spec] §8** : W3C AS2 §4.1 exige `id` IRI absolu sur toutes les activités — `create_activity()` ne l'ajoute pas, introduisant des activités anonymes.

**[grep] Détection dead-code inbox** :
```bash
grep -rn "from.*inbox import\|inbox\." activitypub/urls.py
```
Retourne vide → `inbox.py` n'est jamais importé depuis les URLs.

**Trigger : ≥ 2 gaps + 2 antipatterns + 1 spec** → proposition de patch `ap-protocol-specs.md` pour ajouter :
- Tripwire `transaction.on_commit` dans §3
- Tripwire Date skew dans §2
- Section "dead code detection" dans §0 pre-flight
