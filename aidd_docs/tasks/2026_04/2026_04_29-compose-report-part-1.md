# Instruction: Report — language field migration

## Feature

- **Summary**: Add a `language` field to the `Report` model with choices from `settings.LANGUAGES` and a default derived from `InstanceSettings.get().language`
- **Stack**: `Django 4+`, `PostgreSQL`, `pytest-django`
- **Branch name**: `feat/compose-report`
- **Parent Plan**: `./2026_04_29-compose-report-master.md`
- **Sequence**: `1 of 3`
- Confidence: 9/10
- Time to implement: 20min

## Existing files

- @suddenly/games/models.py
- @suddenly/games/migrations/0007_gamesystem_alter_report_status_and_more.py

### New file to create

- `suddenly/games/migrations/0008_report_language.py`

## User Journey

```
N/A — data model change, no UI
```

## Implementation phases

### Phase 1 — Model

1. Add `language` field to `Report` in `suddenly/games/models.py`:
   - `CharField(max_length=10, choices=settings.LANGUAGES, default="fr")`
   - Default must be a static value `"fr"` (migration constraint — `InstanceSettings` not callable at migration time)
2. Generate migration `0008_report_language.py` via `python manage.py makemigrations games`

### Phase 2 — Tests

1. Add test: creating a `Report` without `language` yields `"fr"` default
2. Add test: `language` accepts only values in `settings.LANGUAGES`

## Validation flow

1. `python manage.py migrate` — applies cleanly
2. `make check` — lint + typecheck + tests pass
