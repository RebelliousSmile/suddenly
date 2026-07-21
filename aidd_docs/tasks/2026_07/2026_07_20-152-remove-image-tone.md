---
objective: >
  #152 « Images : retirer la tonalité ». Supprimer complètement le champ de tonalité (tone),
  ajouté pour l'IA générative abandonnée : deux champs texte libre indépendants
  `games.RapportMedia.tone` et `characters.Character.cover_tone` (CharField, sans enum, absents
  des serializers et de la fédération). Suppression complète (décision utilisateur) : modèles +
  migrations RemoveField (2 apps) + formulaires/templates + affichages figcaption + lectures POST
  + params/écritures services + admin + seed + tests.
success_condition: >
  cd app && python manage.py makemigrations --check --dry-run
  && pytest tests/games/test_post_composer_services.py tests/games/test_post_composer_views.py tests/characters/test_character_create.py -q --no-cov
  && ruff check . && ruff format --check .
  && mypy suddenly/
  && node design/lint/lint-files.mjs templates/games/_composer.html templates/games/partials/rapport_item.html templates/games/partials/rapport_content.html templates/characters/character_create.html
plan_kind: simple
confidence: 9
iteration: 1
created_at: 2026-07-20
---

# #152 « Images : retirer la tonalité » — suppression complète du champ tone

## Objectif

Le champ « tonalité » d'une image a été ajouté pour l'IA générative, que le projet n'utilisera
pas. L'issue demande de le retirer des formulaires d'ajout d'images. **Décision utilisateur :
suppression complète** (pas seulement les formulaires) — laisser les colonnes + l'affichage en
légende laisserait des valeurs mortes et une tonalité résiduelle sur les images existantes.

Deux champs **indépendants**, tous deux `CharField(max_length=80, blank=True)`, **sans enum, sans
default, absents des serializers DRF et de la fédération ActivityPub** :
- `games.RapportMedia.tone` (image d'un post)
- `characters.Character.cover_tone` (couverture d'un personnage)

## Contexte technique vérifié

| Site | Emplacement | Action |
|------|-------------|--------|
| Modèle post-image | `suddenly/games/models.py` `RapportMedia.tone` | Retirer le champ |
| Modèle couverture | `suddenly/characters/models.py` `Character.cover_tone` | Retirer le champ |
| Input composer | `templates/games/_composer.html` (`name="media_tone"`) | Retirer l'input |
| Input add-image inline | `templates/games/partials/rapport_item.html` (`name="tone"`) | Retirer l'input |
| Input couverture | `templates/characters/character_create.html` (`name="cover_tone"`) | Retirer le bloc |
| Affichage figcaption | `rapport_item.html` + `rapport_content.html` (`· <em>{{ media.tone }}</em>`) | Retirer la partie tone, garder `media.alt` |
| Lecture POST composer | `suddenly/games/composer_views.py` (`media_tone`) | Retirer |
| Lecture POST scène | `suddenly/games/report_views.py` (`media_tone`) | Retirer |
| Écriture directe | `suddenly/games/rapport_views.py` (`media.tone = ...`) | Retirer |
| Lecture POST perso | `suddenly/characters/front_views.py` (`cover_tone` + passage) | Retirer |
| Service média | `suddenly/games/services.py` `_attach_rapport_media` (+ `create_scene_post`, `open_new_scene`) | Retirer param `media_tone` + `tone=` |
| Service perso | `suddenly/characters/services.py` `create_character_with_sheet` | Retirer param `cover_tone` + `cover_tone=` |
| Admin | `suddenly/games/admin.py` `RapportMediaInline.fields` | Retirer `"tone"` |
| Seed | `suddenly/core/management/commands/seed_demo.py` (`MEDIA_TONES_*`, pool, `tone=`) | Retirer |
| Tests | `test_post_composer_services.py`, `test_post_composer_views.py`, `test_character_create.py` | Retirer assertions/params tone |

Confirmé : **aucun** serializer/API/ActivityPub ne touche `tone` (grep vide). Les wireframes
(`templates/wireframes/**`, `aidd_docs/wireframes/**`) sont **exemptés** — non servis, non modifiés.

## Milestones
- **M1** : retirer les 2 champs modèle → `makemigrations` (1 RemoveField par app : `games` 0027,
  `characters` 0021).
- **M2** : templates (inputs + figcaptions), vues (4 lectures POST + 1 écriture directe), services
  (params + écritures), admin, seed.
- **M3** : tests (retrait des assertions/params tone) + plan doc + vérif complète + PR `Closes #152`.

## Vérification
- `makemigrations --check` = No changes après commit ; `ruff check .` + `ruff format --check .`
  (repo-wide) ; `mypy suddenly/` ; design lint des 4 templates touchés ; tests ciblés verts.

## Points de vigilance
- **Zéro impact fédération** : `tone` n'est ni sérialisé ni ingéré → suppression sûre.
- **Migrations RemoveField** additives-inverses : perte des données `tone` existantes (voulu).
- **CI lint repo-wide** (leçon #154) : `ruff check .` **et** `ruff format --check .` sur tout le repo.
- **Wireframes exemptés** : ne pas toucher `templates/wireframes/**` ni `aidd_docs/wireframes/**`.

## Évaluation de confiance : 9/10
Suppression mécanique, périmètre entièrement cartographié, aucun dangling après retrait, aucun
couplage fédération. Risque résiduel minime (assertions de tests à nettoyer, migrations inverses).
