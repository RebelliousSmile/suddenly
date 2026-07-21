---
objective: >
  #148 — PR 3 : création « identity-first » + persistance par ligne (②, décision utilisateur).
  Le formulaire de création ne construit plus les traits/actions en mémoire (payload JSON caché) ;
  il crée l'identité puis redirige vers l'éditeur, où traits et actions se gèrent un par un
  (persistés + éditables, cf. PR 2).
success_condition: >
  cd app && python manage.py check && python manage.py makemigrations --check --dry-run
  && pytest tests/characters/test_character_create.py tests/characters/test_character_edit.py tests/characters/test_trait_views.py tests/core/test_i18n.py -q --no-cov
  && ruff check . && ruff format --check . && mypy suddenly/
  && node design/lint/lint-files.mjs templates/characters/character_create.html
plan_kind: simple
confidence: 8
iteration: 1
created_at: 2026-07-21
---

# #148 fiche personnage — PR 3 : création identity-first (②)

## Objectif

Point ② de l'issue : « il n'y a pas de bouton pour valider l'ajout d'un trait/action, il faut en
ajouter un nouveau pour que le précédent soit enregistré ». Cause : le formulaire de création
accumulait traits/actions en **mémoire Alpine** puis les sérialisait dans un champ caché `payload`
soumis en un seul POST atomique — rien n'était persisté au fil de l'eau.

**Décision utilisateur : persistance par ligne** (« puisqu'on peut les éditer », cf. PR 2). Comme un
trait/action doit référencer un personnage existant, la création passe en **deux temps** :
1. Le formulaire crée l'**identité** (nom, description, background, secrets, cover_alt, sheet_url,
   avatar, partie d'origine) via `create_character_with_sheet(..., trait_sets=[], actions=[])`.
2. Redirection vers `characters:traits_editor` — traits/actions ajoutés **un par un** (persistés +
   éditables, PR 2).

## Contexte technique vérifié

| Site | Action |
|------|--------|
| `character_create.html` | Retrait des cartes builder Traits + Actions (Alpine `sets`/`actions`) et du champ caché `payload`. Note « traits & actions ajoutés sur la fiche après création ». Identité + fiche externe conservées |
| `frontend/src/main.js` `characterCreate` | Réduit à `hasName`/`hasGame`/`canSubmit`/`init`/`onSubmit` — retrait de `sets`/`actions`/`buildPayload`/etc. |
| `front_views.py` `character_create` | POST lit l'identité, crée avec listes vides, **redirige vers `traits_editor`**. Retrait du parsing `payload` |
| `front_views.py` | Suppression de `_parse_character_create_payload`, `_is_plain_int`, constantes `MAX_*`, import `json`/`Any` |
| `create_character_with_sheet` (service) | **Inchangé** — garde `trait_sets`/`actions` (tests/seeds) ; le create view passe `[]` |

## Tests
- Vue : POST identité → 302 vers `traits_editor`, personnage créé (PC), **0 trait / 0 action**.
- GET : composant Alpine câblé, **pas** de champ `payload`.
- Erreurs conservées : nom vide / partie manquante / partie non possédée → 422.
- Service (`TestCreateCharacterWithSheet`) inchangé et vert (le service crée toujours des traits
  quand on lui en passe).

## Vérification
- `manage.py check` ; `makemigrations --check` = No changes (aucun champ) ; tests ciblés verts
  (57) ; `ruff check .` + `format --check .` ; `mypy suddenly/` ; design lint `character_create.html`.

## Points de vigilance
- **main.js** rebâti en CI (« Build frontend ») — composant réduit, aucune interpolation.
- **i18n** : msgid long de la note sur **une seule ligne** en fr (contrainte
  `test_no_empty_msgstr_in_fr_po`) ; msgids traits/actions du builder devenus inutilisés (inoffensif).
- **Reste #148** : ⑤ conséquences conditionnelles (PR 4, nouveau modèle `ActionOutcome`).

## Évaluation de confiance : 8/10
Refactor propre (retrait d'un flux entier), service intact, tests réécrits. Risque résiduel : JS non
testable localement (rebâti en CI), et l'UX bascule en deux temps (voulu).
