---
objective: >
  #148 — PR 2 : éditer les traits/actions existants (③). L'éditeur ne faisait que créer +
  supprimer ; on ajoute l'édition en place (lot, trait, action) via HTMX inline, sur le même
  patron « swap du bloc #set-<pk> » que l'existant.
success_condition: >
  cd app && python manage.py check
  && pytest tests/characters/test_trait_views.py tests/core/test_i18n.py::TestNoFuzzyTranslations -q --no-cov
  && ruff check . && ruff format --check . && mypy suddenly/
  && node design/lint/lint-files.mjs templates/characters/partials/trait_set.html
plan_kind: simple
confidence: 9
iteration: 1
created_at: 2026-07-21
---

# #148 fiche personnage — PR 2 : édition des traits/actions (③)

## Objectif

L'éditeur (`traits_editor` + `trait_set.html`) ne proposait que **créer** et **supprimer** un lot/
trait/action — impossible de modifier après coup (il fallait supprimer puis recréer). PR 2 ajoute
l'**édition en place**, prérequis à la persistance par ligne à la création (② PR 3, décision
utilisateur).

## Contexte technique vérifié

Patron existant : chaque action HTMX **swappe le bloc entier `#set-<pk>`** (`hx-target`/`outerHTML`)
— jamais un layout cassé. On garde ce patron pour l'édition : un bouton crayon charge un formulaire
inline dans le bloc, la sauvegarde re-render le bloc « propre », « Annuler » recharge le bloc.

| Site | Action |
|------|--------|
| `trait_views.py` `_render_set` | Params `editing_kind`/`editing_pk` → met une ligne en mode édition |
| `trait_views.py` (nouveau) | `trait_set_card` (GET, cible « Annuler ») · `trait_set_edit` · `trait_edit` · `action_edit` (GET charge le form, POST sauve) |
| `front_urls.py` | 4 routes : `.../sets/<pk>/card/`, `.../sets/<pk>/edit/`, `.../traits/<pk>/edit/`, `.../actions/<pk>/edit/` |
| `partials/trait_set.html` | En-tête, chaque trait, chaque action : affichage + crayon, OU formulaire inline si en édition. Réutilise `TraitSetForm`/`TraitForm`/`ActionForm` |

Dual GET/POST → garde interne `if request.method != "POST"` (le GET sert le formulaire), pas de
`@require_POST` (règle htmx-patterns, exception endpoint double).

## Décisions

- **Valeur du trait à l'édition** : input `number` simple (optionnel → `None` si vide), plutôt que
  le sélecteur −5/+5/free/none du formulaire de création — plus simple, sans Alpine, même résultat
  (`TraitForm.value` = `IntegerField(required=False)`).
- **Frontière d'archi respectée** : rien n'est évalué ; on édite du texte affiché.

## Tests
- `trait_edit` GET rend le form inline (valeur pré-remplie) ; POST met à jour name/value/note ;
  vidage de valeur → `None`.
- `trait_set_edit` renomme le lot ; `action_edit` met à jour name/condition/outcome/traits.
- `trait_set_card` rend le bloc propre ; étranger interdit (403, pas de modif).

## Vérification
- `manage.py check` ; tests ciblés verts (26 + i18n) ; `ruff check .` + `format --check .` ;
  `mypy suddenly/` ; design lint `trait_set.html`. Aucune migration (pas de champ modèle).

## Points de vigilance
- **Swap `#set-<pk>`** partout — cohérent avec create/delete existants ; « Annuler » via
  `trait_set_card` (GET propre).
- **i18n** : nouveaux msgids « Rename », « Concept name », « Trait name », « Value », « Action
  name » ; fr sur une ligne ; `.mo` recompilés.
- **Reste #148** : ② création identity-first / persistance par ligne (PR 3) ; ⑤ conséquences
  conditionnelles (PR 4).

## Évaluation de confiance : 9/10
Ajout mécanique sur un patron éprouvé, réutilise les forms, aucune migration.
