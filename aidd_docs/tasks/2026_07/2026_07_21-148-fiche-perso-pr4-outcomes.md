---
objective: >
  #148 — PR 4 (dernière) : conséquences conditionnelles (⑤). Une action peut porter plusieurs
  résultats choisis par une condition en texte libre (« 7-9 »). Nouveau modèle enfant
  `ActionOutcome` ; gestion inline (ajout + édition + suppression) dans l'éditeur ; affichage sur
  la fiche. Ferme #148.
success_condition: >
  cd app && python manage.py check && python manage.py makemigrations --check --dry-run
  && pytest tests/characters/test_trait_views.py tests/core/test_i18n.py -q --no-cov
  && ruff check . && ruff format --check . && mypy suddenly/
  && node design/lint/lint-files.mjs templates/characters/partials/trait_set.html templates/characters/partials/transverse_actions.html
plan_kind: simple
confidence: 8
iteration: 1
created_at: 2026-07-21
---

# #148 fiche personnage — PR 4 : conséquences conditionnelles (⑤)

## Objectif

Point ⑤ de l'issue : « pour les actions, pour la conséquence, plusieurs résultats selon des
conditions (de 7 à 9, choisis une option) ». Aujourd'hui `Action.outcome` = un seul texte.

Décision utilisateur : **texte libre** pour la condition (aucune validation de plage — cohérent
avec « Suddenly n'évalue rien ») ; **édition inline** des lignes en v1 (comme le reste depuis PR 2).

## Contexte technique vérifié

| Site | Action |
|------|--------|
| `models.py` | Nouveau `ActionOutcome(BaseModel)` : `action` FK (`related_name="outcomes"`), `trigger` (CharField 100, blank), `text` (TextField), `order`. Index sur `action` |
| Migration | `0023_actionoutcome` (CreateModel) |
| `forms.py` | `ActionOutcomeForm` (`trigger`, `text`) |
| `trait_views.py` | `action_outcome_create` / `action_outcome_edit` / `action_outcome_delete` — swap du bloc `#set-<pk>` ; helper `_get_editable_action` (set-scoped only) ; `_render_set` préfetch `actions__outcomes` |
| `front_urls.py` | 3 routes outcomes |
| `partials/trait_set.html` | Sous chaque action : liste des conséquences (badge trigger + texte) avec édition inline + suppression, et un formulaire d'ajout. Read-only si `editable=False` (fiche) |
| `partials/transverse_actions.html` | Affichage read-only des conséquences (legacy) |
| `services.py` / `front_views.py` | Préfetch `actions__outcomes` / `outcomes` (anti-N+1) |

## Décisions

- **`Action.outcome` conservé** (résultat simple/base, legacy) ; `ActionOutcome` = liste
  additionnelle « choisir selon condition ». Non destructif, aucune migration de données.
- **Actions transverses** (`trait_set=None`) restent read-only : l'endpoint outcomes est set-scoped
  (`action__trait_set__character`) → une action transverse renvoie 404 (non atteignable), leurs
  conséquences éventuelles s'affichent en lecture seule.
- **`trigger` texte libre**, aucune validation de plage.

## Tests
- Création (avec/sans trigger), `text` requis (422), édition inline (GET form + POST update),
  suppression, action transverse → 404, étranger → 403, affichage sur la fiche publique.

## Vérification
- `manage.py check` ; `makemigrations --check` = No changes après commit ; tests ciblés verts
  (35 traits + i18n) ; `ruff check .` + `format --check .` ; `mypy suddenly/` (garde
  `trait_set is None` pour narrower le type nullable) ; design lint des 2 templates.

## Points de vigilance
- **mypy** : `outcome.action.trait_set` est `TraitSet | None` → garde `if trait_set is None`.
- **i18n** : nouveaux msgids (« 7-9… », « Condition », « Result… », « Result », « Add a conditional
  result… ») ; fr sur une ligne ; `.mo` recompilés.
- **Fédération** : méta-modèle non sérialisé (extension AP différée #118) → `ActionOutcome` non
  fédéré, cohérent.
- **Bytes littéral** : assertions de test avec accents via `.decode()`, pas `b"…"`.

## Évaluation de confiance : 8/10
Modèle enfant + CRUD inline sur un patron éprouvé (PR 2). Non destructif. Referme #148.
