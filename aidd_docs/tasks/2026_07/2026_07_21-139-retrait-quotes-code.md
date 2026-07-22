---
objective: >
  Épique #139 — retrait complet (hard delete) de la fonctionnalité Quotes. PR 1 = tout le code
  (modèle+migration, UI/routes/templates, API, fédération avec arrêt silencieux, cron, seed,
  tests). Les docs/mémoire (#145) font l'objet d'une PR 2 séparée.
success_condition: >
  cd app && python manage.py check && python manage.py makemigrations --check --dry-run
  && ruff check . && ruff format --check . && mypy suddenly/
  && pytest -q --no-cov (978 passed ; 7 échecs environnementaux connus — cascade du test de
     concurrence, passent en isolation)
plan_kind: simple
confidence: 8
iteration: 1
created_at: 2026-07-21
---

# Épique #139 — retrait des Quotes (PR 1 : code)

## Objectif

`Quote` est un modèle parallèle redondant avec `Rapport(kind=DISCUSSION)` (surdimensionné vs sa
valeur). L'épique #139 le retire en **hard delete**. PR 1 supprime tout le code ; PR 2 purgera
docs/mémoire (#145).

## Périmètre couvert (couche par couche)

| Couche | Fichiers |
|--------|----------|
| Modèle (#140) | `characters/models.py` (`Quote`, `QuoteVisibility`, `QuoteQuerySet`, contrainte/index, `EPHEMERAL_QUOTE_TTL_HOURS`), `core/models.py` (`UserUsageStats.total_quotes`) |
| Migrations | `characters/0024_delete_quote.py`, `core/0011_remove_userusagestats_total_quotes.py` (destructives, voulu) |
| Admin | `characters/admin.py` |
| UI/routes | `characters/front_views.py` (`quote_add` + contexte `quotes`), `front_urls.py` ; `games/front_views.py` (`quote_create`/`quote_delete`), `front_urls.py`, `report_views.py`, `rapport_views.py`, `game_views.py`, `_view_helpers.py` ; `core/views.py` (page quotes + `instance_quotes`), `docs/nav.py` |
| Templates | Supprimés : `quotes/_quote_card`, `characters/_quote_card`, `characters/_quote_form`, `core/quotes` ; nettoyés : `characters/detail`, `games/report_detail`, `core/home`, `stories/detail`, `characters/_list_results`, `_char_link` (exemple de commentaire), `core/privacy` |
| API | `core/serializers.py` (`QuoteSerializer`, `quotes_count`), `characters/api_urls.py`, `characters/views.py` |
| Fédération (#142) | `activitypub/serializers.py` (`serialize_quote`, `suddenly:quotes`), `signals.py`, `tasks.py`, `views.py` (outbox perso → collection vide). **Arrêt silencieux** : aucun `Delete` émis ; un inbound quote-Note tombe dans le drop par défaut (pas de 500) |
| Cron (#144) | `activitypub/tasks.py` (`cleanup_expired_quotes`) + `config/settings/base.py` (`CELERY_BEAT_SCHEDULE`) |
| Seed | `core/management/commands/seed_demo.py` |
| Tests | `tests/games/test_citations.py` supprimé ; nettoyage `test_activitypub`, `test_models`, `test_new_models`, `test_views`, `test_character_edit`, `test_game_completion`, `factories.py` |

Empreinte : **1222 suppressions / 22 ajouts** sur 40 fichiers.

## Décision — `total_quotes` sûr à retirer

`UserUsageStats.total_quotes` était un champ **mort** (jamais lu/écrit) ; le compteur de don utilise
`total_posts` + `posts_since_last_prompt`. Aucun couplage → suppression sans risque.

## Vérification
- `makemigrations --check` = No changes ; `manage.py check` OK ; `ruff check .` + `format --check .` ;
  `mypy suddenly/` ; **grep `quote` = plus aucune ref réelle hors migrations historiques**.
- `pytest` : 978 passed. Les 7 échecs sont l'**artefact environnemental documenté** (le test de
  concurrence `test_parallel_requests_serialize_via_row_lock` laisse une session ouverte et cascade
  des ERROR sur les tests suivants du batch) : le test de concurrence ET la classe
  `TestLinkOfferFederation` **passent en isolation** ; la CI (fresh DB) était verte avec ce test sur
  les 6 PR précédentes.

## Points de vigilance
- **Migrations destructives** : perte des données Quote (voulu, #139).
- **Fédération** : arrêt silencieux — les Notes déjà fédérées restent chez les instances distantes
  (résidu accepté) ; l'outbox personnage renvoie une collection vide.
- **PR 2** : purge docs/mémoire (#145).

## Évaluation de confiance : 8/10
Retrait mécanique exhaustif, vérifié statiquement (ruff/mypy/check) + suite verte hors artefact
environnemental connu. Risque résiduel : détails de fédération inbound (couverts par la suite AP).
