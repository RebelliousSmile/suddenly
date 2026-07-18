---
objective: Supprimer le dispatcher inbox mort de tasks.py et propager l'extrait normatif DEC-038 dans les règles auto-chargées.
success_condition: pytest tests/test_activitypub.py -q && ruff check suddenly/activitypub
iteration: 0
created_at: 2026-07-18T00:00:00+02:00
plan_kind: simple
parent: 2026_07_18-adr-038-offer-federation-loop-master.md
confidence: 9
---

# Part 4 — Nettoyage code mort + propagation normative

Indépendant des Parts 1-3. Livrable à tout moment.

## A. Supprimer le doublon mort de `tasks.py`

- `tasks.py::process_incoming_activity` route vers des stubs no-op
  (`handle_offer`/`handle_accept`/`handle_reject`/`handle_create`/`handle_update`/`handle_delete`)
  qui ne font que logger — ils doublonnent les vrais handlers de `inbox.py`.
- DEC-038 §4 : « candidat à suppression pour lever l'ambiguïté avec `inbox.py::handle_offer` ».

### Tâches

1. **Vérifier que c'est bien mort** — grep global :
   `grep -rn "process_incoming_activity" suddenly/ tests/ config/` — confirmer **aucun** `.delay()`
   ni appel direct. Si des appels existent, **ne pas supprimer** : router vers `inbox.py` à la place
   (re-planifier).
2. **Supprimer** `process_incoming_activity` + le `Protocol _ActivityHandler` associé + les stubs
   no-op `handle_*` de `tasks.py` (garder les tasks d'émission : `deliver_activity`,
   `send_accept_activity`, `send_reject_activity`, etc.).
3. Vérifier qu'aucun import cassé ne subsiste (`ruff check`, `mypy`).

## B. Propager l'extrait normatif dans `08-activitypub.md`

- Ajouter à `.claude/rules/08-domain/08-activitypub.md` (contexte auto-chargé) une section
  « Format Offer canonique (DEC-038) », style bullets (règle 1-rule-writing) :
  - Format Offer canonique = `serialize_link_request` (`object.type = suddenly:Claim/Adopt/Fork`,
    cible en `target`, message en `object.content`, PJ en `object.proposedCharacter`).
  - Réception via `inbox.py::handle_offer` **uniquement** ; ne jamais réintroduire la forme `Relationship`.
  - Résoudre un personnage cible par `_resolve_character_by_actor_url` (ap_id distant, sinon parse
    de l'URL locale).
  - (Après Part 1) Accept fédéré corrélé par l'`id` de l'Offer d'origine (`origin_offer_id`),
    jamais par la PK locale.

## Critère de succès

`pytest tests/test_activitypub.py -q` vert (aucune régression) + `ruff check suddenly/activitypub` propre.
Le fichier `08-activitypub.md` contient la section DEC-038.

## Amendements 🤖 (implémenté 2026-07-18)

- 🤖 **Mort confirmé** : `grep` global → aucun `.delay()` ni appel direct de `process_incoming_activity`. Seule référence : un test `@pytest.mark.skip` (`test_inbox_accepts_valid_activity`) qui patche `views.process_incoming_activity` — jamais exécuté, laissé tel quel.
- 🤖 **Suppression élargie** : retiré `process_incoming_activity`, le `Protocol _ActivityHandler`, ET tous les handlers d'entrée de `tasks.py` (`handle_follow`/`handle_undo`/`handle_create`/`handle_update`/`handle_delete`/`handle_accept`/`handle_reject`/`handle_offer`) — tous morts une fois le dispatcher retiré, tous doublonnant `inbox.py`. Import `Protocol` retiré. Tasks d'émission conservées (dont `send_accept_follow`, testée directement).
- 🤖 **Test e2e obsolète corrigé** (hors périmètre initial mais requis par DEC-038) : `TestOfferIncoming.test_offer_incoming_creates_link_request` envoyait la forme `Relationship` abandonnée → migré au format canonique `suddenly:Adopt` (target top-level, message en `object.content`), aligné sur ses tests frères `TestAcceptIncoming`/`TestRejectIncoming`.
- Section « Offer federation — canonical format (DEC-038) » ajoutée à `08-activitypub.md`.
