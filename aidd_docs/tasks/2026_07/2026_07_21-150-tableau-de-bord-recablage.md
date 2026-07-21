---
objective: >
  #150 « Tableau de bord » — PR 1 (recâblage). Le nom « Tableau de bord » était pris par le
  dashboard MJ (`characters:gm_dashboard`), désormais inutile : la distinction MJ/joueur est
  contextuelle (droits par partie), pas une page dédiée. Supprimer le dashboard MJ et faire de
  la zone d'admin d'instance (`gmh`) LE « Tableau de bord » (réservé `is_admin`).
success_condition: >
  cd app && python manage.py check && python manage.py makemigrations --check --dry-run
  && pytest tests/core/test_home_and_menu.py -q --no-cov
  && ruff check . && ruff format --check . && mypy suddenly/
  && node design/lint/lint-files.mjs templates/gmh/base.html templates/gmh/dashboard.html templates/components/_user_menu_items.html
plan_kind: simple
confidence: 9
iteration: 1
created_at: 2026-07-21
---

# #150 « Tableau de bord » — PR 1 : recâblage

## Objectif

L'issue décrit une page **admin de modération** nommée « Tableau de bord ». Or ce libellé pointe
aujourd'hui vers le **dashboard MJ** (`characters:gm_dashboard`), pendant que la vraie zone de
modération (`gmh`, `/gmh/`) est cachée derrière un lien « Admin ». Décision utilisateur : le
dashboard MJ n'a plus lieu d'être (droits MJ/joueur = contextuels par partie), donc on libère le
nom et on le donne à `gmh`.

Cette PR 1 est un **recâblage pur** (aucun champ modèle, 0 migration). Le contenu de modération
(file des contenus signalés, stats de fédération) fera l'objet d'une **PR 2**.

## Contexte technique vérifié

Le dashboard MJ n'héberge **aucune fonction unique** : il agrège PNJ + demandes de lien, or
l'arbitrage a déjà sa page dédiée (`characters:link_requests`, lien « Requests ») et les PNJ sont
listables ailleurs. Suppression sûre. Son seul `{% include %}` (`components/link_request_card.html`)
est partagé — conservé.

| Site | Action |
|------|--------|
| `suddenly/characters/gm_views.py` | Supprimé (ne contenait que `gm_dashboard`) |
| `suddenly/characters/front_urls.py` | Retrait import `gm_views` + route `dashboard/` |
| `templates/characters/gm_dashboard.html` | Supprimé |
| `templates/components/_user_menu_items.html` | Retrait lien dashboard MJ ; lien admin « Admin » → « Dashboard » (FR « Tableau de bord »), icône `layout-dashboard`, toujours `is_admin` |
| `templates/gmh/base.html` | En-tête section « Administration » → « Dashboard » ; item nav « Dashboard » → « Overview » (évite « Tableau de bord > Tableau de bord ») |
| `templates/gmh/dashboard.html` | `<title>` → « Dashboard » ; `<h1>` → « Overview » |
| `tests/core/test_home_and_menu.py` | Retrait assertion `gm_dashboard` ; nouveau test `dashboard_link_admin_only` (visible admin, absent joueur) |

## i18n

- Réutilise « Dashboard » (existant → FR « Tableau de bord »).
- Un nouveau msgid : « Overview » → FR « Vue d'ensemble ». fr/en + `.mo` recompilés.
- « Administration » / « Admin » deviennent inutilisés (inoffensif, laissés en place).

## Vérification
- `manage.py check` OK (URLconf charge sans `gm_views`) ; `makemigrations --check` = No changes ;
  `ruff check .` + `format --check .` ; `mypy suddenly/` ; design lint des 3 templates ;
  `test_home_and_menu.py` vert (6 tests).

## Points de vigilance
- **Aucune migration** : recâblage UI/URL pur.
- **`gmh` reste gardé** par `@admin_required` (`User.is_admin`) — l'entrée menu l'est aussi.
- **PR 2 à suivre** : file `ContentReport` (contenus signalés) + section stats de fédération.

## Évaluation de confiance : 9/10
Suppression mécanique sans fonction orpheline, renommage à faible churn, périmètre cartographié.
