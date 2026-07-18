---
objective: Corréler l'Accept par l'id de l'Offer d'origine pour que l'instance demandeuse retrouve sa LinkRequest.
success_condition: pytest tests/test_activitypub.py -k "LinkOfferFederation" -q && mypy suddenly/activitypub suddenly/characters
iteration: 0
created_at: 2026-07-18T00:00:00+02:00
plan_kind: simple
parent: 2026_07_18-adr-038-offer-federation-loop-master.md
confidence: 9
---

# Part 1 — Corrélation par l'`id` de l'Offer d'origine (round-trip id → Accept)

## Problème

- L'Offer émis par A porte `id = https://A/link-requests/pkA`.
- B reçoit et crée `LinkRequest-B` (PK `pkB` ≠ `pkA`).
- À l'acceptation, `send_accept_activity` fait `serialize_link_request(request-B)` → l'Accept
  référence `https://B/link-requests/pkB`, PK inconnue de A → `handle_accept` échoue.

## Solution

- Persister sur la `LinkRequest` reçue l'`id` de l'Offer d'origine (l'URL de A).
- À l'acceptation d'une demande **d'origine distante**, l'Accept référence cet `id` d'origine,
  pas la PK locale.
- `handle_accept` côté A extrait alors `pkA` et retrouve sa propre `LinkRequest`.

## Tâches

1. **Modèle** — ajouter à `LinkRequest` (`suddenly/characters/models.py`) :
   - `origin_offer_id = models.URLField(max_length=500, blank=True, null=True)` — l'`id` de
     l'Offer entrant (renseigné uniquement pour les demandes d'origine distante ; `null` pour
     les demandes créées localement).
   - Respecter `max_length=500` (règle 08-activitypub : URLField AP).
2. **Migration** — `python manage.py makemigrations characters` → migration additive simple
   (champ nullable, pas de RunPython). Vérifier le SQL via `sqlmigrate`.
3. **Réception** — dans `inbox.py::handle_offer`, stocker `origin_offer_id=activity.get("id")`
   à la création de la `LinkRequest`.
4. **Émission de l'Accept/Reject** — dans `tasks.py::send_accept_activity` et
   `send_reject_activity` :
   - Si `request.origin_offer_id` est renseigné (demande d'origine distante), construire
     l'activité avec `object = request.origin_offer_id` (une **string**, l'id de A).
   - Sinon, conserver le comportement actuel (`serialize_link_request`).
   - Attention : `create_accept_activity(actor, original_activity)` accepte déjà `str | dict` ;
     passer la string garantit que `handle_accept` côté A reçoit un `object` textuel.
5. **Réception de l'Accept** — vérifier que `inbox.py::handle_accept` gère un `object` **string**
   (`_extract_link_request_id` opère déjà sur `str(offer_id)` et le format `/link-requests/`).
   - Note : l'`object` **dict** n'est pas du legacy — c'est le format **actuel** de
     `create_accept_activity(actor, serialize_link_request(...))`. Sur ce dict, `str(offer_id)`
     donne une repr Python bruitée dont `_extract_link_request_id` extrait un pk invalide.
   - En pratique ce chemin dict n'atteint jamais `handle_accept` : `send_accept_activity` skippe
     si `not request.requester.remote`, donc un demandeur local ne reçoit pas d'Accept. Seul le
     chemin **string** (demandeur distant, `object = origin_offer_id`) compte. Mais par robustesse,
     si `object` est un dict, lire `object.get("id")` avant l'extraction.

## Test (garde-fou)

- Étendre `TestLinkOfferFederation` : émettre un Offer de A → ingérer chez B (`handle_offer`) →
  vérifier `origin_offer_id` stocké → construire l'Accept via le chemin d'émission → vérifier
  que son `object` est bien l'`id` de A → rejouer `handle_accept` côté A → la `LinkRequest-A`
  passe `ACCEPTED`.
- Mocker `deliver_activity.delay` (pas de réseau — règle 05-pytest).

## Critère de succès

`pytest tests/test_activitypub.py -k "LinkOfferFederation" -q` vert + `mypy` propre.
