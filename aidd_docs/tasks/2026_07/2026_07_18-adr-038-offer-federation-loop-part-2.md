---
objective: Reconstruire l'état (CharacterLink, SharedSequence, statut) côté demandeur à la réception de l'Accept.
success_condition: pytest tests/test_activitypub.py -k "LinkOfferFederation" -q && pytest tests/characters -q
iteration: 0
created_at: 2026-07-18T00:00:00+02:00
plan_kind: simple
parent: 2026_07_18-adr-038-offer-federation-loop-master.md
depends_on: 2026_07_18-adr-038-offer-federation-loop-part-1.md
confidence: 8
---

# Part 2 — Reconstruction d'état à l'Accept côté demandeur

## Problème

- Aujourd'hui `inbox.py::handle_accept` ne fait que flipper `LinkRequest.status = ACCEPTED`.
- Côté demandeur (A), rien n'est reconstruit : ni `CharacterLink`, ni `SharedSequence`, ni
  transition de statut du personnage. La boucle est fonctionnellement incomplète.

## Contrainte de conception (risque principal)

- `LinkService.accept_request` est écrit **du point de vue de l'instance-cible** (récepteur) :
  il crée un PC pour FORK avec `owner=requester`, transfère l'ownership sur ADOPT, transitionne
  `target_character.status`, annule les `QUEUED`, etc.
- Côté **demandeur** (A) : le `requester` est **local**, la `target_character` est un Character
  **distant** (miroir local avec `ap_id`). Réutiliser `accept_request` tel quel est risqué
  (perspective inversée, re-déclenchement d'Accept, double side-effects).
- **Décision** : introduire une méthode dédiée `LinkService.reconstruct_remote_accept(request)`
  plutôt qu'appeler `accept_request`.

## Tâches

1. **Service** — `LinkService.reconstruct_remote_accept(request, response_message="")` dans
   `suddenly/characters/services.py`, `@transaction.atomic` :
   - Idempotence : si `request.status == ACCEPTED` **et** un `CharacterLink` existe déjà pour
     cette demande → sortir sans rien refaire.
   - Déterminer `source` selon le type (miroir de `accept_request`) :
     - CLAIM → `request.proposed_character`. **Sur A (demandeur), ce PJ est LOCAL** — créé par
       `LinkService.create_request` au moment où le joueur a lancé le claim. Il n'est **pas** null
       (contrairement au côté récepteur B, où Part 3 doit le résoudre). Ne pas dupliquer ici la
       dégradation « null → flip statut » : elle n'a pas lieu d'être côté A.
     - ADOPT → **modèle d'ownership à poser d'abord** (cf. risque master). La `target_character`
       de A est un miroir distant (`remote=True`) de l'objet autoritatif sur B. Décision à figer
       avant de coder : le PC adopté est-il un objet local distinct, ou une mutation du miroir ?
       Probable : représenter l'adoption par un lien vers le miroir sans muter son `owner`/`status`
       (le miroir suit l'objet distant via `Update`).
     - FORK → créer le nouveau PC (`parent=target_character`, `owner=creator=requester`).
   - Créer le `CharacterLink` (status `ACTIVE`) + le `SharedSequence` draft.
   - Passer `request.status = ACCEPTED`, `resolved_at`, `response_message`.
   - **Ne pas** ré-émettre d'Accept (on est le côté demandeur, pas le côté qui accepte) —
     garantir qu'aucun signal `post_save` sur cette `LinkRequest` ne déclenche `send_accept_activity`
     (le statut passe à `ACCEPTED` : le signal `link_request_post_save` enverrait un Accept vers
     `requester` — ici local → skippé, mais à vérifier explicitement pour éviter une boucle).
   - **Notification** : notifier l'utilisateur A que sa demande a été acceptée (le TODO
     « notify both parties » de `accept_request` n'est pas encore implémenté ; poser au moins le
     point d'ancrage ici, même si l'envoi effectif est différé).
2. **Handler** — `inbox.py::handle_accept` : après résolution de la `LinkRequest-A` (Part 1),
   appeler `LinkService.reconstruct_remote_accept(link_request, activity.get("summary", ""))`.
3. **Garde-fou de cohérence** — vérifier que la transition de statut du `target_character`
   distant côté A reste cohérente (le PNJ distant n'est qu'un miroir ; sa transition locale est
   informative). Documenter le choix en commentaire.

## Test

- Prolonger le scénario Part 1 : après `handle_accept` côté A, asserter :
  - `CharacterLink` créé (type correct, `link_request` = la demande),
  - `SharedSequence` draft créé,
  - statut du personnage cible mis à jour,
  - ré-appel de `handle_accept` (replay) → aucun doublon (idempotence).

## Critère de succès

`pytest tests/test_activitypub.py -k "LinkOfferFederation" -q` + `pytest tests/characters -q` verts.

## Résolution & amendements 🤖 (implémenté 2026-07-18)

- 🤖 **Ownership ADOPT cross-instance tranché** : le lien pointe sur le miroir distant sans muter son `owner`/`status` (le miroir suit l'objet autoritatif via `Update`). Le statut du `target_character` distant n'est **pas** transitionné côté demandeur (documenté en commentaire dans `reconstruct_remote_accept`). FORK crée un vrai PC local (`owner=creator=requester`, `parent=miroir`).
- 🤖 **Notification déjà couverte par signal** : le point d'ancrage TODO n'a pas été recodé — `core.notify_on_link_request` (post_save sur `LinkRequest`, statut→`ACCEPTED`) émet déjà la notif `LINK_ACCEPTED` au demandeur. Un `Notification.objects.create` explicite dans le service **doublonnait** (bug attrapé par le test d'idempotence). Retiré ; le service laisse le signal notifier.
- 🤖 Pas de boucle d'Accept : le signal fire `send_accept_activity` mais celui-ci skippe si `requester` non-`remote` (ici local) — vérifié.
- Livré : `LinkService.reconstruct_remote_accept` (`@transaction.atomic`, idempotent) + `inbox.handle_accept` l'appelle après corrélation Part 1.
