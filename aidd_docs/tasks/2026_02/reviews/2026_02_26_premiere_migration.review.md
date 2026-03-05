# Code Review for Première Migration (Phase 1 Fondations)

Setup of dev environment: `.env`, Redis-optional settings, `local` model properties, profile templates.

- Status: resolved
- Confidence: 10/10

## Main expected Changes

- [x] `.env` file created
- [x] `local` property on `User`, `Game`, `Character`
- [x] Redis optional with DB cache fallback in `development.py`
- [x] `suddenly/core/tasks.py` removed (dead duplicate code)
- [x] Profile templates added (bonus from adjacent task)

## Scoring

- [🟢] **core/tasks.py deleted** — no dangling imports confirmed; activitypub/tasks.py covers all cases
- [🟢] **local property** `suddenly/users/models.py:92`, `games/models.py:62`, `characters/models.py:112` — correct type hints + docstrings, consistent across all three models
- [🟢] **actor_url type hints** `suddenly/games/models.py:57`, `characters/models.py:108` — return type `str | None` added, matches User's existing signature
- [🟢] **Redis fallback** `config/settings/development.py:42-62` — clean conditional, DB cache + `CELERY_TASK_ALWAYS_EAGER` correct for sync fallback
- [🟡] **CELERY_TASK_ALWAYS_EAGER deprecated** `config/settings/development.py:57` — still functional in Celery 5 via Django settings bridge, but the modern equivalent is `app.conf.task_always_eager = True`. Low urgency.
- [🟡] **Profile games section always empty** `templates/users/profile.html:62-78` — the "Parties récentes" section has no `{% for game in games %}` loop and `ProfileView` doesn't pass a `games` queryset. Will always render empty state even when games exist. Needs `get_context_data()` override in view.
- [🟡] **preferred_languages raw JSON widget** `templates/users/profile_edit.html:136` + `suddenly/users/forms.py:23` — exposes raw JSON syntax to end users (`["fr", "en"]`). Acceptable for Phase 1 but should be replaced with a comma-separated input before public release.
- [🟢] **File size claim inconsistency** `templates/users/profile_edit.html:104` — "jusqu'à 5 MB" but `DATA_UPLOAD_MAX_MEMORY_SIZE = 10MB` in settings. Non-breaking; just documentation.

## ✅ Code Quality Checklist

### Potentially Unnecessary Elements

- [🟢] No unnecessary elements introduced

### Standards Compliance

- [🟢] Naming conventions followed — `local`, `actor_url` consistent with existing patterns
- [🟢] Coding rules ok — type hints, docstrings, single responsibility
- [🟢] `local` property follows the `is_`, `has_`, `can_` prefix exception correctly (`local` is a domain term, not ambiguous)

### Architecture

- [🟢] Design patterns respected — properties on models, CBV for views
- [🟢] Proper separation of concerns — settings, models, views each in their layer
- [🟢] No business logic in templates

### Code Health

- [🟢] Functions and files sizes — all additions are < 10 lines
- [🟢] No magic numbers/strings
- [🟢] Error handling — templates handle all form error states
- [🟡] `ProfileView` missing `get_context_data()` for games (see scoring above)

### Security

- [🟢] SQL injection risks — ORM only
- [🟢] XSS vulnerabilities — Django auto-escaping active; `|safe` not used
- [🟢] CSRF token present in profile_edit.html
- [🟢] Environment variables secured — `.env` not committed (gitignored)
- [🟢] Data exposure — `private_key` field not exposed in admin fieldsets ✅

### Performance

- [🟢] `ProfileView.get_queryset()` filters on `is_active=True` — bounded queryset
- [🟢] No N+1 risks in current templates (no loops yet)

### Backend specific

#### Logging

- [🟢] Settings changes are configuration-only; no logging needed

## Final Review

- **Score**: 8/10 — All fixes correct, one functional gap in profile template
- **Feedback**: The three core fixes (local property, Redis optional, dead code removal) are clean and complete. The profile templates are a bonus addition that work correctly for viewing but the games section is a stub.
- **Follow-up Actions**:
  1. Add `get_context_data()` to `ProfileView` to pass user's public games
  2. Replace `preferred_languages` JSON textarea with comma-separated input
- **Additional Notes**: `CELERY_TASK_ALWAYS_EAGER` deprecation is Celery 5 only — low priority, no behavior change.
