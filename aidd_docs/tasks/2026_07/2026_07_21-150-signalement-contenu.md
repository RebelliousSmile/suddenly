---
objective: >
  #150 « Tableau de bord » — PR 2. Permettre de signaler un contenu (personnage, scène, partie)
  et le retrouver vite depuis la file de modération admin. Option A (décision utilisateur) :
  réutiliser la mécanique `UserReport` + la file `gmh:reports` existante, plutôt qu'un second
  système parallèle sur `ContentReport`.
success_condition: >
  cd app && python manage.py check && python manage.py makemigrations --check --dry-run
  && pytest tests/core/test_moderation.py -q --no-cov
  && ruff check . && ruff format --check . && mypy suddenly/
  && node design/lint/lint-files.mjs templates/core/report_content_form.html templates/gmh/reports.html templates/characters/detail.html templates/games/detail.html templates/games/report_detail.html
plan_kind: simple
confidence: 8
iteration: 1
created_at: 2026-07-21
---

# #150 « Tableau de bord » — PR 2 : signalement de contenu

## Objectif

L'issue veut « retrouver rapidement un élément signalé (personnage, report, game) problématique ».
Constat : **rien ne permettait de signaler un contenu**. Le seul flux existant était « Signaler un
utilisateur » (`report_user` → `UserReport`, une personne). `ContentReport` (US-27) existe comme
modèle mais **aucun code ne le crée**, aucune file — abandonné au profit de `UserReport` (#136).

**Option A (décision utilisateur)** : réutiliser `UserReport` et la file `gmh:reports` existantes.
Un « Signaler » sur un contenu dépose un `UserReport(reported_user=auteur, context=l'élément)` via
le GFK contexte déjà prévu (scène/personnage). La file affiche un lien direct vers l'élément.
Pas de second système de signalement (règle « Refactor Before Multiplying »).

## Contexte technique vérifié

- `create_user_report(reporter, reported_user, category, comment, context=None)` gère déjà le GFK.
- `UserReport.context` (GFK) = scène (`games.Report`) / personnage (`characters.Character`) /
  partie (`games.Game`). `admin_reports` ne le préchargeait pas.
- Modèles locaux : `Character.owner`/`creator`, `Report.author`, `Game.owner` ; tous portent `remote`.

| Site | Action |
|------|--------|
| `suddenly/core/views.py` | `report_content(kind, pk)` + `_resolve_reportable` (whitelist character/scene/game, local only, garde self-report) |
| `suddenly/core/urls.py` | route `signaler-contenu/<kind>/<uuid:pk>/` |
| `templates/core/report_content_form.html` | formulaire (catégorie + commentaire), réutilise les chaînes de `report_user_form` |
| `templates/characters/detail.html` · `games/detail.html` · `games/report_detail.html` | bouton « Signaler » (icône flag), visible aux non-auteurs authentifiés |
| `suddenly/core/admin_views.py` | `admin_reports` : `prefetch_related("context")` + `_context_link` → lignes `{report, context_url, context_kind}` |
| `templates/gmh/reports.html` | itère `report_rows` ; lien vers l'élément signalé quand présent |

## Comportement

- Signaler une scène → `UserReport(reported_user=scene.author, context=scene)`.
- Signaler un personnage → `reported_user = owner or creator`.
- Signaler une partie → `reported_user = game.owner`.
- Auto-signalement (auteur = signaleur) ou contenu inexistant/distant → refus (redirect / 404).
- L'auteur signalé n'est jamais notifié (DEC-F6 — inchangé).
- Bloquer depuis la file bannit l'auteur ET résout le signalement (comportement existant).

## i18n

Réutilise « Reason », « Submit report », « Please select a reason. », « Report submitted… ».
Nouveaux msgids : `Report %(label)s`, l'avertissement du formulaire, `Report this
character/game/scene`, `You cannot report your own content.`, `an untitled scene`,
`Flagged %(kind)s:`, `character`/`scene`/`game`. fr/en + `.mo` recompilés (babel).

## Vérification
- `manage.py check` ; `makemigrations --check` = No changes (aucun champ modèle) ;
  `pytest tests/core/test_moderation.py` (47) ; `ruff` + `mypy suddenly/` ; design lint des 5
  templates ; render OK des pages détail (report_detail_actions, citations, trait_views).

## Points de vigilance
- **Aucune migration** : `UserReport`/`ContentReport` inchangés ; on branche l'existant.
- **`_resolve_reportable`** : variables nommées par branche (pas de `obj` réutilisé) — sinon mypy
  confond les types de modèles.
- **`ContentReport` laissé tel quel** (modèle + Django admin) — non supprimé, hors périmètre.
- **Whitelist stricte** des `kind` + `remote=False` : pas de signalement de contenu distant (le
  ban agit sur un utilisateur local).

## Évaluation de confiance : 8/10
Réutilisation propre de la mécanique existante, périmètre cartographié. Risque résiduel : choix du
« responsable » d'un personnage (owner vs creator) et couverture UI des boutons.
