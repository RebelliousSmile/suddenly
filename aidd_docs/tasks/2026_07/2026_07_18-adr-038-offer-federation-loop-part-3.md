---
objective: Résoudre un proposedCharacter distant inconnu en le fetchant via ActivityPub au lieu de le laisser null.
success_condition: pytest tests/test_activitypub.py -k "LinkOfferFederation or remote_character" -q && mypy suddenly/activitypub
iteration: 0
created_at: 2026-07-18T00:00:00+02:00
plan_kind: simple
parent: 2026_07_18-adr-038-offer-federation-loop-master.md
confidence: 8
---

# Part 3 — Résolution du PJ distant (`proposedCharacter`)

> **Prérequis dur pour tout CLAIM cross-instance** (pas un simple renforcement) — voir master.

## Problème

- Dans `inbox.py::handle_offer`, `proposedCharacter` est résolu **best-effort** via
  `_resolve_character_by_actor_url` → `null` si le PJ distant n'est pas déjà connu localement.
- **Conséquence bloquante** : côté récepteur (B), quand la cible accepte, `accept_request` fait
  `source = request.proposed_character` et `CharacterLink.source` est **non-null**
  (`models.py:411`). Un `proposed_character` null → `CharacterLink.objects.create(source=None)` →
  **IntegrityError** à l'acceptation. Sans Part 3, un CLAIM cross-instance **crashe** à l'accept.

## Solution

- Si la résolution locale échoue, **fetcher** l'acteur Character distant et créer un miroir
  local (`remote=True`, `ap_id`, `origin_game` synthétisé).
- Aucun helper de fetch de Character n'existe → en créer un, routé par `_http.fetch_ap_json`.

## Tâches

1. **Helper** — `get_or_create_remote_character(actor_url)` dans `inbox.py` :
   - `Character.objects.filter(ap_id=actor_url).first()` d'abord (déjà connu).
   - Sinon `fetch_ap_json(actor_url, accept=..., timeout=...)` (SSRF hardening obligatoire —
     règle ap-pivots §9 ; jamais `httpx` brut).
   - Mapper le JSON-LD (type `Person`) → `Character` : `name`, `ap_id`, `remote=True`,
     `origin_game` **synthétisé** (règle 08-characters : `origin_game` non-null, tout Character
     distant en reçoit un — réutiliser le mécanisme existant côté `handle_create`/inbox).
   - `get_or_create` idempotent sur `ap_id`.
2. **Intégration** — dans `handle_offer`, si `_resolve_character_by_actor_url(obj.get("proposedCharacter"))`
   renvoie `None` et qu'une URL est présente → tenter `get_or_create_remote_character`.
   - Rester tolérant : si le fetch échoue (réseau, 404), retomber sur `null` (best-effort
     préservé, pas d'exception qui casserait la réception de l'Offer).
2b. **Filet anti-crash à l'acceptation (obligatoire)** — même avec Part 3, le fetch peut échouer
   → `proposed_character` peut rester `null` sur un CLAIM. Ajouter un guard dans le chemin
   d'acceptation (`accept_request`, branche CLAIM, ou en amont dans `handle_accept`/la vue
   d'acceptation) : si `type == CLAIM` et `proposed_character is None` → **rejeter/mettre en
   attente** la demande avec un message explicite, jamais laisser l'`IntegrityError` remonter.
   Ce filet est livrable indépendamment et protège même hors CLAIM cross-instance.
3. **Cohérence origin_game** — vérifier comment les Characters distants existants obtiennent
   leur `origin_game` synthétisé (cf. `inbox.py` `handle_create`) et réutiliser exactement ce
   mécanisme pour ne pas diverger.

## Test

- `handle_offer` avec un `proposedCharacter` inconnu + fetch mocké (`respx`/`mocker` — pas de
  réseau) → asserter qu'un Character distant est créé (`remote=True`, bon `ap_id`,
  `origin_game` non-null) et rattaché à la `LinkRequest`.
- Cas fetch en échec → `proposed_character` reste `null`, la `LinkRequest` est quand même créée.

## Critère de succès

`pytest tests/test_activitypub.py -k "LinkOfferFederation or remote_character" -q` vert + `mypy` propre.

## Résolution & amendements 🤖 (implémenté 2026-07-18, vérifié 2026-07-19)

- 🤖 Helper `get_or_create_remote_character(actor_url)` livré dans `inbox.py` : lookup par `ap_id` d'abord, sinon fetch via `_http.fetch_ap_actor` (→ `fetch_ap_json`, SSRF-safe, ap-pivots §9 — jamais httpx brut). Résout l'auteur via `creator`/`owner`/`attributedTo`, synthétise un `Game` distant par domaine (`ap_id = https://<domain>`) pour l'`origin_game` non-null (08-characters), puis `get_or_create` idempotent sur `ap_id`. Tolérant : tout échec de fetch renvoie `None` → l'Offer n'est pas droppé.
- 🤖 Intégration dans `handle_offer` : si `_resolve_character_by_actor_url(proposedCharacter)` renvoie `None` et qu'une URL est présente → fallback `get_or_create_remote_character`. `origin_offer_id` toujours stocké (Part 1).
- 🤖 **Filet anti-crash (task 2b) posé dans le service, pas dans le handler** : `LinkService.accept_request` garde en tête de la branche CLAIM — `if request.proposed_character is None: raise ValidationError(...)` (`services.py:157-166`) avant tout `CharacterLink.objects.create(source=...)`. L'`IntegrityError` sur `source` non-null ne remonte jamais ; l'acceptation est rejetée proprement. Filet centralisé (couvre CLAIM local ET cross-instance) plutôt que dupliqué dans `handle_accept`/la vue.
- 🤖 Tests livrés dans `TestLinkOfferFederation` (couverts par le filtre `LinkOfferFederation`) : `test_offer_fetches_unknown_remote_proposed_character` (fetch mocké → miroir `remote=True`, `ap_id` correct, `origin_game` non-null) et `test_offer_with_unresolvable_proposed_character_degrades_to_null` (fetch → `None` → `proposed_character` null mais `LinkRequest` créée). Aucun réseau (mock `_http.fetch_ap_actor`, 05-pytest).
- Vérifié 2026-07-19 : `pytest tests/test_activitypub.py tests/characters` vert (fresh DB) + `mypy suddenly/activitypub suddenly/characters` sans erreur.
