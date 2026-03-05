# Instruction: Première Migration — Phase 1 Fondations

## Feature

- **Summary**: Set up local dev environment, run all migrations, create superuser, and validate the full Phase 1 foundation is operational
- **Stack**: `Python 3.12`, `Django 5.x`, `PostgreSQL 15+`, `psycopg3`
- **Branch name**: `feat/premiere-migration`

## Existing files

- @scripts/init-dev.sh
- @config/settings/development.py
- @suddenly/users/migrations/0001_initial.py
- @suddenly/users/migrations/0002_user_language_prefs.py
- @suddenly/games/migrations/0001_initial.py
- @suddenly/games/migrations/0002_reportcast_character_fk.py
- @suddenly/activitypub/migrations/0001_initial.py
- @suddenly/characters/migrations/0001_initial.py
- @manage.py
- @requirements.txt

### New file to create

- `.env` — local environment variables (DATABASE_URL, SECRET_KEY, DJANGO_SETTINGS_MODULE)

## Implementation phases

### Phase 0 — PostgreSQL Setup

> Create DB user and database before anything else

1. `createuser -P suddenly` — create user with password `suddenly`
2. `createdb -O suddenly suddenly` — create DB owned by that user
3. Verify: `psql -U suddenly -d suddenly -c "\conninfo"`

### Phase 1 — Environment Setup

> Create virtual environment, install dependencies, write `.env`

1. Create venv: `python -m venv .venv`
2. Activate: `.venv/Scripts/activate` (Windows) or `source .venv/bin/activate`
3. Install deps: `pip install -r requirements.txt`
4. Create `.env` with at minimum:
   - `DJANGO_SETTINGS_MODULE=config.settings.development`
   - `DATABASE_URL=postgres://suddenly:suddenly@localhost:5432/suddenly`

### Phase 2 — Database Initialization

> Verify config, apply migrations, create superuser

1. `python manage.py check` — fix any errors before continuing
2. `python manage.py showmigrations` — verify all migrations detected
3. `python manage.py migrate` — apply all pending migrations
4. `python manage.py createsuperuser` — create admin account

### Phase 3 — Validation

> Confirm the app is fully operational through manual and shell checks

1. `python manage.py runserver`
2. Verify URLs: `/`, `/admin/`, `/accounts/login/`, `/accounts/signup/`
3. Log into `/admin/` with superuser — confirm Users, Games, ActivityPub sections present
4. Shell smoke test:
   - `User.objects.count()`, `Game.objects.create(...)`, `game.local == True`

## Reviewed implementation

<!-- Filled by review agent -->

- [x] Phase 0 — PostgreSQL Setup (manuel)
- [x] Phase 1 — Environment Setup (`.env` créé, Redis optionnel, `core/tasks.py` supprimé)
- [ ] Phase 2 — Database Initialization (manuel)
- [ ] Phase 3 — Validation (manuel)

## Validation flow

1. `psql -U suddenly -d suddenly` connects without error
2. `python manage.py check` returns no errors
2. `python manage.py showmigrations` shows all migrations applied (`[X]`)
3. `/admin/` loads and shows Users, Games, Fédération sections
4. Can create a User and a Game via admin
5. Shell: `game.local == True` (i.e. `game.remote == False`), `game.ap_id is None`

## Estimations

- Confidence: 9/10
  - ✅ Migrations already created and ready
  - ✅ Dev settings have sensible defaults (no `.env` strictly required)
  - ✅ `init-dev.sh` covers most steps as reference
  - ❌ PostgreSQL must already be running with `suddenly` DB + user created (external dependency)
- Time to implement: ~20 min
