# Plan correctif — findings High de l'audit sc-python (2026-07-15)

**Périmètre** : les findings de sévérité **High** remontés par `aidd-dev:reviewer` sur deux passes (surfaces critiques + zones non couvertes). Read-only jusqu'ici ; ce plan décrit l'implémentation, non appliquée.

**Branche suggérée** : `fix/audit-high-ssrf-linkservice`

## Carte des fixes

| # | Finding | Fichier | Sévérité | Statut plan |
|---|---|---|---|---|
| 1 | SSRF WebFinger (2 chemins) | `activitypub/federation_views.py` + `users/settings_views.py` | High | fix confiant |
| 2 | Bypass `LinkService` API | `characters/views.py` | High | fix confiant |
| 3 | Ingest non-atomic + broadcast prématuré | `games/ingest.py` + `activitypub/signals.py` | High | fix confiant |
| 4 | CSV import : HTTP bloquant par ligne | `users/settings_views.py` | High | fix (refactor Celery) |
| D | Divergence règle↔code sur transition de statut | `characters/services.py` vs `08-characters.md` | — | **décision requise** |

> Le finding « sequence_validate_publish laisse le perso NPC » du reviewer est **écarté** : `accept_request` transitionne déjà le statut à l'acceptation (cf. section D). Ce n'est pas un bug de correction mais une divergence de conception.

## Statut d'implémentation — 2026-07-15 ✅

**Tout implémenté, non committé.** `mypy` clean (45 fichiers), `ruff` clean, **358 passed / 22 skipped** (e2e exclus).

- **Fix 1-4** appliqués tels que décrits ci-dessous.
- **Section D → Option A retenue** (et non B) : après lecture du code + tests, la transition-à-l'acceptation s'est révélée **testée et référencée `DEC-035`** (`tests/characters/test_link_service.py`). Réécrire la state machine aurait révoqué une décision délibérée. → j'ai corrigé la **règle** `08-characters.md` pour refléter le code, ajouté `LinkService.publish_sequence` (statut PUBLISHED + notification `SHARED_SEQUENCE` aux deux parties, atomic), délégué `sequence_validate_publish`, corrigé le docstring stale de `SharedSequence`. 4 tests ajoutés.
- Note : `.claude/rules/08-characters.md` est gitignored → correction locale/non suivie.
- Fix 3 : `on_commit` posé dans `report_post_save` (couvre aussi le Medium `on_commit` de la 1re passe) ; `bulk_create` sur `ReportCast` validé (aucun signal sauté).
- Fix 4 : task `import_follows_from_rows` + fallback inline si broker down ; prod eager sans `REDIS_URL` (offload réel seulement avec broker).

> La section D ci-dessous décrit encore les **deux** options A/B pour trace ; **c'est A qui a été appliquée**.

---

## Fix 1 — SSRF : `_lookup_webfinger` contourne le garde SSRF

### Problème

`suddenly/activitypub/federation_views.py:186-189` fetch `https://{domain}/.well-known/webfinger` avec un `httpx.Client(timeout=10)` **brut**, sur un `domain` extrait de la requête de recherche utilisateur (`user@instance`). Le reste du module passe par `_http.fetch_ap_actor`, qui résout l'hôte une fois, bloque les IP privées/loopback/link-local et épingle l'IP validée (anti DNS-rebinding). Cette requête WebFinger **saute entièrement** cette protection.

- Viole : `ap-pivots-django-activitypub.md` §9 (SSRF), `08-activitypub.md` (Federation), pivot plugin `protocol/activitypub-django.md` §4.
- Scénario d'échec : recherche `@x@169.254.169.254` ou `@x@localhost` → requête sortante vers un hôte interne **avant** toute validation. Exfiltration métadonnées cloud (169.254.169.254), scan de ports internes.

### Solution

Extraire la logique resolve + pin + block de `fetch_ap_actor` dans un helper réutilisable de `_http.py`, puis router WebFinger à travers.

**`suddenly/activitypub/_http.py`** — refactor :

1. Extraire une fonction `_resolve_and_pin(parsed) -> tuple[str, dict, dict] | None` qui retourne `(request_url, extra_headers, extensions)` ou `None` si bloqué (scheme non autorisé, hostname absent, IP bloquée). Elle contient les lignes actuelles 60-99.
2. Ajouter un fetch générique :
   ```python
   def fetch_ap_json(url: str, *, accept: str, timeout: int = 10) -> dict[str, Any] | None:
       """SSRF-safe GET returning parsed JSON, or None on any failure."""
       parsed = urlparse(url)
       pinned = _resolve_and_pin(parsed)  # None → blocked/invalid
       if pinned is None and _needs_pinning(parsed):
           return None
       request_url, extra_headers, extensions = pinned or (url, {}, {})
       headers = {"Accept": accept, **extra_headers}
       try:
           with httpx.Client(timeout=timeout, follow_redirects=False) as client:
               resp = client.get(request_url, headers=headers, extensions=extensions)
           if resp.status_code == 200:
               return resp.json()
       except Exception:
           logger.warning("Failed to fetch %s", url, exc_info=True)
       return None
   ```
3. `fetch_ap_actor` devient un mince wrapper :
   ```python
   def fetch_ap_actor(url: str, *, timeout: int = 10) -> dict[str, Any] | None:
       return fetch_ap_json(
           url, accept="application/activity+json, application/ld+json", timeout=timeout
       )
   ```
   → comportement identique préservé (mêmes headers, même timeout, même follow_redirects=False).

**`suddenly/activitypub/federation_views.py:176-214`** — `_lookup_webfinger` :

- Remplacer le bloc `httpx.Client` brut par :
  ```python
  from ._http import fetch_ap_json
  url = f"https://{domain}/.well-known/webfinger?resource=acct:{address}"
  data = fetch_ap_json(url, accept="application/jrd+json")
  if not data:
      return []
  links = data.get("links", [])
  ```
- Supprimer l'import local `import httpx` devenu inutile dans la fonction.
- `_fetch_actor` (ligne 260) délègue déjà à la version sûre — inchangé.

**`suddenly/users/settings_views.py:424-444`** — `_resolve_and_follow` (SSRF #2, même racine) :

- **Deuxième chemin WebFinger non protégé**, identique au précédent : `httpx.Client(timeout=10)` brut sur un `domain` issu d'un CSV utilisateur, puis `get_or_create_remote_user(actor_url)` sur l'`actor_url` retourné — aucune validation SSRF sur les deux fetch.
- Remplacer le bloc `httpx` (424-436) par le même `fetch_ap_json(url, accept="application/jrd+json")`.
- `actor_url` : avant `get_or_create_remote_user`, s'assurer qu'il passe aussi par le fetch SSRF-safe (`get_or_create_remote_user` doit utiliser `fetch_ap_actor`, à vérifier — sinon router via `fetch_ap_json`).
- Supprimer l'`import httpx` du module s'il n'a plus d'autre usage.

> Ce point justifie l'extraction du helper partagé plutôt qu'un patch local : **deux** call sites WebFinger dupliqués avec le même trou. Rule of three non atteint (2 sites) mais la sécurité prime → mutualiser.

### Vérification

- Test SSRF (les deux sites) : `pytest` avec `_lookup_webfinger("x@127.0.0.1")`, `_resolve_and_follow(user, "x@169.254.169.254")` → `[]` / `False`, aucune requête émise (mock `socket.getaddrinfo` ou `respx` : zéro call). Modèle : pivot §11 "Test SSRF".
- Test nominal : `respx` mock un WebFinger + actor distant valide → résolution OK (non-régression) sur les deux chemins.
- `rtk mypy suddenly/activitypub/ suddenly/users/` → 0 erreur (strict mode).

---

## Fix 2 — `LinkRequestViewSet.reject`/`.cancel` court-circuitent `LinkService`

### Problème

`suddenly/characters/views.py:255-268` (`reject`) et `:284-294` (`cancel`) mutent `link_request.status` directement et `save()`, sans appeler `LinkService`. Résultat : `_promote_next_queued` ne s'exécute jamais depuis l'API.

- Viole : `08-characters.md` ("All link operations go through `LinkService`"), invariant de file d'attente (`03-django-services.md`).
- Scénario d'échec : personnage A a une requête PENDING R1 + une requête QUEUED R2. Le créateur rejette R1 **via l'API** → R2 reste `QUEUED` à vie, file en deadlock, le demandeur de R2 n'est jamais notifié. Le chemin HTMX (non-API), lui, passe probablement par le service → incohérence entre les deux surfaces.

### Solution

Déléguer au service, garder le contrôle de permission dans la vue (auth = vue, domaine = service).

**`suddenly/characters/views.py`** — `reject` (garder les checks 403 lignes 249-253, remplacer 255-268) :
```python
from django.core.exceptions import ValidationError
from .services import LinkService

# ... après le check 403 ...
try:
    LinkService.reject_request(
        link_request, response_message=request.data.get("message", "")
    )
except ValidationError as exc:
    return Response(
        {"error": exc.messages[0] if exc.messages else str(exc)},
        status=status.HTTP_400_BAD_REQUEST,
    )
link_request.refresh_from_db()
serializer = LinkRequestSerializer(link_request)
return Response(serializer.data)
```
→ le check `status != PENDING` (ligne 255-258) est désormais porté par le service (`reject_request` lève `ValidationError` si non-PENDING) — supprimer le doublon dans la vue.

**`cancel`** (garder le check 403 requester, remplacer 284-291) :
```python
try:
    LinkService.cancel_request(link_request)
except ValidationError as exc:
    return Response(
        {"error": exc.messages[0] if exc.messages else str(exc)},
        status=status.HTTP_400_BAD_REQUEST,
    )
link_request.refresh_from_db()
serializer = LinkRequestSerializer(link_request)
return Response(serializer.data)
```
→ note : `cancel_request` autorise PENDING **et** QUEUED (service ligne 288), alors que la vue actuelle n'autorise que PENDING. C'est une **amélioration** cohérente avec le domaine (un demandeur peut annuler une requête en file). À confirmer : garder ce comportement élargi (recommandé) ou restreindre.

### Durcissement lié (même fichier service)

`LinkService.reject_request` (services.py:263) et `cancel_request` (:284) enchaînent plusieurs mutations (`request.save()` + `_promote_next_queued` → `save()` + `Notification.objects.create()`) **sans** `@transaction.atomic`, contrairement à `revoke_link` (:304). Un crash entre le save de la requête et la promotion laisse la file dans un état incohérent.

- Ajouter `@transaction.atomic` sur `reject_request` et `cancel_request` (décorateur déjà importé, cf. `revoke_link`).
- Conforme à `03-django-services.md` ("Wrap multi-step mutations in `transaction.atomic()`").

### Vérification

- Test file d'attente : créer R1 (PENDING) + R2 (QUEUED) sur le même personnage → `POST /api/link-requests/{R1}/reject/` → R1 REJECTED **et** R2 promue PENDING + Notification créée. C'est le scénario d'échec exact.
- Test permission : non-créateur → 403 ; non-demandeur sur cancel → 403 (non-régression).
- Test 400 : reject sur une requête déjà résolue → 400 avec message.
- `rtk mypy suddenly/characters/` → 0 erreur.

---

---

## Fix 3 — Ingest : création non-atomique + broadcast AP prématuré

### Problème

`suddenly/games/ingest.py:131-158` : `Report.objects.create(..., status=PUBLISHED)` puis boucles `ReportCast.objects.create` / `Rapport.objects.create`, **sans `transaction.atomic`**. Or `activitypub/signals.py:report_post_save` appelle `_safe_delay(send_create_activity, "report", id)` **au `create()`** (vérifié : pas de `transaction.on_commit`).

- Conséquence 1 : le `Create` AP est enfilé **avant** que les `ReportCast`/`Rapport` existent → un peer peut fetcher un report à moitié peuplé.
- Conséquence 2 : un échec en milieu de boucle laisse un report `PUBLISHED` partiel **déjà broadcasté**, non rollbackable.
- Viole : `03-django-services.md` (multi-step → `transaction.atomic`), `ap-pivots-django-activitypub.md` §3 (`on_commit` avant `.delay()`).

### Solution

Deux niveaux, complémentaires :

1. **`games/ingest.py`** — envelopper le bloc création (131-158) dans `with transaction.atomic():` pour garantir que report + cast + rapports commitent ensemble (ou rollback complet).
2. **`activitypub/signals.py:report_post_save`** — différer le broadcast : remplacer l'appel direct `_safe_delay(...)` par `transaction.on_commit(lambda: _safe_delay(send_create_activity, "report", instance.id))`. Fixe aussi le finding Medium `on_commit` de la 1re passe, pour **tous** les chemins de publication (pas seulement l'ingest).
   - ⚠ Interaction : avec `on_commit`, le broadcast ne part qu'après le commit du bloc atomic → children garantis présents. Sans le point 2, wrapper l'ingest en atomic ne suffit pas (le signal fire au `create()` synchrone, avant le commit).
   - Vérifier que `on_commit` hors transaction (chemins déjà auto-commit) s'exécute immédiatement — comportement Django natif, non-régression.

### Vérification

- Test atomicité : forcer une exception sur le 2e `Rapport.objects.create` (mock) → aucun `Report` en base, aucun `send_create_activity` enfilé (`CELERY_TASK_ALWAYS_EAGER=True` + spy sur la task).
- Test ordre broadcast : `CELERY_TASK_ALWAYS_EAGER=True`, capturer que la task voit les `ReportCast`/`Rapport` existants au moment de son exécution.
- `rtk pytest suddenly/games/ -m "not e2e"`.

---

## Fix 4 — CSV import : N appels HTTP synchrones bloquants par ligne

### Problème

`suddenly/users/settings_views.py:126-135` : `import_follows_csv` boucle sur chaque ligne CSV → `_resolve_and_follow` → **1 GET WebFinger synchrone (timeout 10s) par ligne**, dans le handler de requête. Un CSV de N lignes = N appels séquentiels bloquants → worker monopolisé, requête qui peut dépasser toute limite de timeout Gunicorn.

- Viole : pivot `httpx` §9 (jamais d'appels indépendants séquentiels — offload), pivot `celery` (appartient à une task de fond).
- Aggravant (`:426`) : `httpx.Client` réinstancié **par ligne** — aucune réutilisation de connexion.

### Solution

Refactor vers un traitement asynchrone (dépend de Fix 1 pour la partie SSRF) :

1. **Nouvelle task Celery** `import_follows_from_rows(user_id, rows)` dans `users/tasks.py` (créer si absent) :
   - Parse les lignes hors-requête, appelle `_resolve_and_follow` (désormais SSRF-safe via Fix 1).
   - **Un seul `httpx.Client`** réutilisé pour tout l'import (ou via `fetch_ap_json` qui gère son client — acceptable car tasks distinctes).
   - Idempotence : `Follow.objects.get_or_create` déjà en place côté follow ; vérifier no-op sur re-run.
2. **`import_follows_csv`** : lire le CSV, valider, enfiler la task, retourner immédiatement un état « en cours » (partial HTMX). Pas de comptage synchrone `imported/errors` — le rendu final passe par un statut task (ou un simple message « import lancé »).
   - ⚠ Décision UX : afficher un compteur live (nécessite polling/statut task) ou un simple « import lancé, suivez vos abonnements » ? **Recommandé** : message simple au MVP, pas de polling.

### Vérification

- Test : `CELERY_TASK_ALWAYS_EAGER=True`, POST CSV 3 lignes → task exécutée, 3 `Follow` créés, réponse HTTP immédiate (pas de N×10s).
- Test SSRF hérité de Fix 1 (le chemin passe par `fetch_ap_json`).
- `rtk mypy suddenly/users/`.

> Si le refactor Celery est jugé trop lourd pour ce lot, **fallback minimal** : garder le traitement synchrone mais (a) appliquer Fix 1 (SSRF), (b) réutiliser un seul `httpx.Client`, (c) borner le nombre de lignes (ex. 200 max). La partie « bloquant worker » resterait, à traiter plus tard.

---

## Section D — Divergence règle↔code : quand transitionne le statut du personnage ?

**Pas un fix — décision de conception requise avant toute action.**

### Constat

`08-characters.md` (règle normative) affirme :
- « Create `CharacterLink` on link request acceptance, but keep status pending until SharedSequence is published »
- « Character status changes (NPC → CLAIMED/ADOPTED/FORKED) **only** on SharedSequence publication »

Mais `characters/services.py:accept_request` (140-220) fait **à l'acceptation** :
- transition `target_character.status` → `CLAIMED`/`ADOPTED` (182-190)
- `CharacterLink.objects.create(...)` sans statut pending (197-202)
- `SharedSequence.objects.create(...)` draft (205-209)

Et `sequence_validate_publish` (`sequence_views.py:179`) met juste `status=PUBLISHED` sur la séquence, avec deux TODO (transition statut, notification).

### Pourquoi le finding « High » du reviewer est écarté

Le scénario « claim publié mais perso reste NPC » **ne se produit pas** : le perso est déjà `CLAIMED`/`ADOPTED` depuis l'acceptation. Implémenter le TODO de `sequence_validate_publish` **re-transitionnerait** un statut déjà changé → double effet, pas une correction.

### Les deux options (à trancher par l'utilisateur)

- **Option A — le code fait foi, la règle est périmée.** La transition à l'acceptation est le comportement voulu (plus simple, pas d'état « pending »). → Action : corriger `08-characters.md` pour refléter « transition à l'acceptation », supprimer les mentions « pending until published », retirer les TODO trompeurs de `sequence_validate_publish` (ne garder que la notification de publication, qui elle manque réellement).
- **Option B — la règle fait foi, le code est en avance de phase.** Le statut ne devrait changer qu'à la publication. → Action (refactor plus lourd) : introduire un statut `CharacterLink` pending, déplacer la transition de statut + l'activation du lien de `accept_request` vers `sequence_validate_publish`, gérer l'expiration des liens jamais publiés (déjà évoquée dans la règle). Impacte la file d'attente et l'`accept_request`.

### Point réellement manquant (indépendant du choix A/B)

- `sequence_validate_publish` ne crée **aucune notification** à la publication (TODO:183) — à combler dans les deux options.
- `accept_request` a aussi `# TODO: Notify both parties` (218) — notification d'acceptation manquante.

---

## Hors périmètre (signalé, non traité ici)

- `# TODO: Send ActivityPub Reject(Offer)` (`views.py:265`) + `Accept` (`services.py:217`) : livraison AP des réponses de lien, avec `transaction.on_commit(lambda: deliver_activity.delay(...))` — dépend du câblage delivery des liens.
- Findings Medium/Low restants (N+1 DRF, dead code inbox `tasks.py`, Content-Type sortant `ld+json`, pagination outbox, `@require_POST` manquants ×5, middleware i18n sans `deactivate`, rate-limit non atomique, `dispatch_uid` manquant…) : lot séparé, non bloquants.

## Séquencement

1. **Section D d'abord** — trancher A/B ; conditionne s'il y a du travail sur `accept_request`/`sequence_validate_publish`.
2. Fix 1 (SSRF, 2 sites) — isolé, débloque la partie sécurité de Fix 4.
3. Fix 2 (LinkService API) — isolé.
4. Fix 3 (ingest atomic + `on_commit` signal) — isolé, mais `on_commit` touche tous les chemins de publication → tester large.
5. Fix 4 (CSV import Celery) — dépend de Fix 1.
6. `rtk pytest -m "not e2e"` complet + `rtk mypy suddenly/` avant commit.
