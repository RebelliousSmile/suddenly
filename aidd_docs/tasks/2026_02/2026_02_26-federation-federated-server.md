# Instruction: FederatedServer model

## Feature

- **Summary**: Add `FederatedServer` model to track known remote ActivityPub instances (domain, software type/version, status, stats). Foundation structure — no federation logic yet.
- **Stack**: `Django 5.x`, `PostgreSQL`, `Python 3.12`
- **Branch name**: `main`

## Existing files

- `suddenly/activitypub/models.py` — add FederatedServer here (file may not exist yet)
- `suddenly/activitypub/admin.py` — register FederatedServer
- `suddenly/core/models.py` — BaseModel (UUID pk + timestamps)

### New files to create

- `suddenly/activitypub/migrations/0001_initial.py` — first migration for activitypub app
- `tests/test_federation.py` — contract tests

## Implementation phases

### Phase 1: FederatedServer model

> Add model + migration + admin to the existing activitypub app

1. Create `suddenly/activitypub/models.py` with `ServerStatus` choices + `FederatedServer(BaseModel)`
   - Fields: `server_name` (unique), `application_type`, `application_version`, `status`, `user_count`, `last_checked`
   - Method: `is_suddenly_instance() -> bool`
   - Indexes on `server_name`, `status`, `application_type`
2. Generate migration (`makemigrations activitypub`)
3. Register in `suddenly/activitypub/admin.py` with list_display, list_filter, search

### Phase 2: Tests

> Contract tests for model behavior

1. `test_federated_server_str` — `__str__` returns domain name
2. `test_is_suddenly_instance_true` — application_type="suddenly" returns True
3. `test_is_suddenly_instance_false` — other type returns False
4. `test_default_status_is_unknown` — new server defaults to UNKNOWN

## Reviewed implementation

- [ ] Phase 1
- [ ] Phase 2

## Validation flow

1. `python manage.py makemigrations activitypub` — no errors
2. `python manage.py migrate` — applies cleanly
3. `FederatedServer.objects.create(server_name="test.social")` — works in shell
4. Tests pass

## Estimations

- Confidence: 9/10
  - ✅ BaseModel pattern already established
  - ✅ activitypub app already wired in INSTALLED_APPS
  - ✅ No circular deps, no cross-app FK
  - ❌ activitypub/models.py may not exist yet — needs verification
- Time: ~20 min
