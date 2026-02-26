# Instruction: Audit Fixes — Suddenly `code/`

## Feature

- **Summary**: Address all critical and major issues identified in the 2026-02-26 audit of `code/`. Focus on security, federation completeness, code quality, and static analysis tooling.
- **Stack**: `Python 3.12`, `Django 5.x`, `Django REST Framework`, `Celery`, `PostgreSQL 16`
- **Branch name**: `fix/audit-2026-02-26`
- **Scope**: `code/` repository (remote: `github.com/RebelliousSmile/suddenly`)

## Existing files

- @code/suddenly/settings.py
- @code/suddenly/activitypub/signatures.py
- @code/suddenly/activitypub/inbox.py
- @code/suddenly/activitypub/tasks.py
- @code/suddenly/activitypub/activities.py
- @code/suddenly/characters/services.py
- @code/suddenly/characters/views.py
- @code/suddenly/core/serializers.py
- @code/suddenly/characters/models.py
- @code/suddenly/users/models.py
- @code/suddenly/games/models.py

### New files to create

- `code/suddenly/activitypub/models.py` — `ProcessedActivity` model for inbox deduplication
- `code/tests/test_signatures.py` — Tests for HTTP signature creation and verification
- `code/tests/test_inbox.py` — Tests for inbox handlers
- `code/mypy.ini` — mypy strict configuration (Phase 5, before Phase 4)
- `code/.ruff.toml` — ruff linter configuration (Phase 5, before Phase 4)

---

## Implementation phases

### Phase 1 — Security (prod blockers)

> Fix all issues that create security vulnerabilities or allow bypass of federation trust.

1. `settings.py:16` — Remove SECRET_KEY default value, raise `ImproperlyConfigured` if not set
2. `activitypub/signatures.py` — Cache fetched public keys in `FederatedServer.public_key` (DB), add 10s timeout on HTTP fetch; re-fetch only if field is empty
3. `activitypub/inbox.py:332` — Validate actor URL domain matches the request's `FederatedServer` before `get_or_create_remote_user()`; reject with 403 if mismatch
4. `activitypub/inbox.py` — Add `ProcessedActivity` model with unique `ap_id`; skip silently if already processed

### Phase 2 — Federation completeness (functional blockers)

> Make federation actually work end-to-end by sending all outgoing activities. Only send to remote actors (`local=False`).

1. `characters/services.py:126-127` — Send `Offer` activity on `create_request()` via `deliver_activity.delay()` — only if target character's owner is remote
2. `characters/services.py:203` — Send `Accept` / `Reject` activity on `accept_request()` / `reject_request()` — only if requester is remote
3. `characters/views.py:170,198,230,333,364` — Remove 5 TODO stubs, wire to updated service methods
4. `characters/services.py:52-55` — Wrap pending request check in `select_for_update()` inside existing `@transaction.atomic` — verify decorator is present, add if missing

### Phase 3 — Static analysis tooling

> Configure linters first so type hints added in Phase 4 can be validated immediately.

1. `mypy.ini` — Configure mypy strict mode scoped to `suddenly/` package
2. `.ruff.toml` — Configure ruff with Django rules (`DJ`, `E`, `W`, `F`, `I`)
3. Run `mypy` + `ruff` on current codebase, fix reported issues before proceeding

### Phase 4 — Code quality

> Add type hints and tests on critical modules with zero coverage. Use mypy from Phase 3 to validate as you go.

1. `characters/services.py` — Add full type hints to all `LinkService` methods
2. `activitypub/inbox.py` — Add full type hints to all handler functions
3. `activitypub/signatures.py` — Complete partial type hints
4. `characters/views.py:126-233` — Extract `_create_link_request(link_type)` to deduplicate claim/adopt/fork (moved from Performance — this is a refactor, not a perf fix)
5. `tests/test_signatures.py` — Write tests: valid signature, invalid signature, expired signature, missing header
6. `tests/test_inbox.py` — Write tests: Follow, Create, Offer (claim/adopt/fork), Accept, Reject handlers

### Phase 5 — Performance (prod impact)

> Eliminate N+1 queries that degrade performance under load.

1. `core/serializers.py:40-44` — Replace `get_games_count()` / `get_characters_count()` with `annotate()` on queryset
2. `core/serializers.py:124-131` — Replace `get_appearances_count()` with `annotate()`
3. `characters/models.py` — Add missing `db_index=True` on `ap_id` and `local` fields

---

## Reviewed implementation

- [ ] Phase 1 — Security
- [ ] Phase 2 — Federation completeness
- [ ] Phase 3 — Static analysis tooling
- [ ] Phase 4 — Code quality
- [ ] Phase 5 — Performance

---

## Validation flow

1. `SECRET_KEY` not set → `ImproperlyConfigured` raised on startup, not silent
2. Send Offer from instance A → instance B inbox receives it → `LinkRequest` created on B
3. Accept on B → `Accept` activity sent to A → `CharacterLink` created on A
4. Local-only Claim (both actors on same instance) → no `deliver_activity` call triggered
5. Concurrent `create_request()` on same NPC → only one succeeds, second raises validation error
6. `UserDetailSerializer` with 100 users → single query (annotated count), not 101
7. `verify_signature()` called twice for same actor → second call uses `FederatedServer.public_key` from DB (no HTTP)
8. Replay same `ap_id` activity → second call silently ignored
9. Actor domain mismatch in inbox → 403 returned, no user created
10. `mypy . --strict` exits 0
11. `ruff check .` exits 0

---

## Estimations

- **Confidence**: 8/10 — Phase 2 depends on verifying `@transaction.atomic` presence in `create_request()`; Phase 4 tests require reading exact inbox handler contracts before writing.
- **Time to implement**: Phase 1: 2h — Phase 2: 3h — Phase 3: 1h — Phase 4: 4h — Phase 5: 1h — Total: ~11h
