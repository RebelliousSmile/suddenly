---
objective: >
  #151 « violence ». Exposer l'avertissement de contenu (Report.content_warning, déjà affiché
  en voile/spoiler sur la scène) dans le composer en mode feed (nouvelle scène). Champ texte
  libre + bouton preset « Violence ». Option A retenue (utilisateur) : réutiliser le champ
  scène existant, pas de CW par post sur Rapport.
success_condition: >
  cd app && python manage.py makemigrations --check --dry-run
  && pytest tests/games/test_post_composer_services.py tests/games/test_post_composer_views.py -q --no-cov
  && ruff check . && ruff format --check .
  && mypy suddenly/
  && node design/lint/lint-files.mjs templates/games/_composer.html
plan_kind: simple
confidence: 9
iteration: 1
created_at: 2026-07-20
---

# #151 « violence » — avertissement de contenu dans le composer

## Objectif

Le voile spoiler existe déjà à la lecture (`report_detail.html` masque une scène derrière son
`content_warning`), et la page de composition longue (`report_compose.html`) offre le champ. Mais
le composer rapide (feed / nouvelle scène) ne l'expose pas — impossible d'avertir « Violence » en
ouvrant une scène depuis le fil. L'issue demande l'option de prévention.

**Décision utilisateur — Option A** : exposer le champ scène existant (`Report.content_warning`,
`CharField(max_length=500, blank=True)`) dans le composer en mode feed. Pas d'ajout d'un CW par
post sur `Rapport`.

## Contexte technique vérifié

| Site | Emplacement | Action |
|------|-------------|--------|
| Champ modèle | `Report.content_warning` | Existe déjà — aucun changement, aucune migration |
| Composer (feed) | `templates/games/_composer.html` (sheet « envoi », branche `{% if not frozen %}`) | Ajouter input `name="content_warning"` + bouton preset « Violence » |
| État Alpine | `_composer.html` x-data | Ajouter `cw: ''` + `x-model="cw"` |
| Vue POST | `suddenly/games/composer_views.py` (~L84) | Lire `content_warning`, passer à `open_new_scene` |
| Service | `suddenly/games/services.py` `open_new_scene` | Param `content_warning: str = ""`, écrit sur `Report.objects.create` |

Le mode **frozen** (ajout d'un post à une scène existante via `scene_post_create`) ne porte pas
le CW — c'est une propriété de scène, pas de post. L'input est donc gardé `{% if not frozen %}`.

## i18n

- Réutilise les msgids existants de `report_compose.html` : « Content warning »,
  « e.g. Violence, dark themes », « If filled, content will be hidden behind a 'Show' button. »
- Un seul nouveau msgid : « Violence » (bouton preset) — ajouté fr/en + `.mo` recompilés (babel).

## Milestones
- **M1** : input CW + preset « Violence » dans le composer (feed only), état Alpine `cw`.
- **M2** : lecture POST (`composer_views`) + param/écriture service (`open_new_scene`).
- **M3** : tests (service + vue) + i18n + plan doc + vérif complète + PR `Closes #151`.

## Vérification
- `makemigrations --check` = No changes (aucun champ ajouté) ; `ruff check .` + `ruff format --check .`
  repo-wide ; `mypy suddenly/` ; design lint `_composer.html` ; tests composer verts.

## Points de vigilance
- **Frozen guard** : le CW ne s'applique qu'à la nouvelle scène (feed) — jamais en mode frozen.
- **Alpine rule** : preset injecté via `data-cw` + `$el.dataset` + `escapejs`, pas d'interpolation JS.
- **`@keydown.enter.prevent`** sur l'input pour ne pas soumettre le form (rule m2m-edit-views).
- **DRY i18n** : réutilisation des chaînes CW existantes, un seul msgid neuf.

## Évaluation de confiance : 9/10
Changement additif, champ modèle déjà présent (zéro migration), périmètre restreint au composer
feed. Risque résiduel minime (placement UI dans la sheet d'envoi, cohérence Alpine).
