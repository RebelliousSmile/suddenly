<!-- migrated from docs – verify with /init -->
# Coding Guidelines

> Ces règles doivent être vérifiées après CHAQUE génération de code.

## Requirements to complete a feature

**A feature is really completed if ALL of the above are satisfied: iterate until all are green.**

## Commands to run

### Single command (recommended)

| Command | Description |
| ------- | ----------- |
| `make check` | Lint + typecheck + tests + coverage (fail_under=80%) |

### Individual commands

| Order | Command | Description |
| ----- | ------- | ----------- |
| 1 | `ruff check .` | Lint Python |
| 2 | `ruff format --check .` | Format check |
| 3 | `mypy suddenly/` | Type checking (strict) |
| 4 | `pytest` | Tests with coverage (80% threshold) |

### Automated gates

- **Pre-commit**: ruff + mypy run automatically on `git commit`
- **CI**: GitHub Actions blocks merge on any failure

## Coding Conventions

### Naming

| Élément | Convention | Exemple |
|---------|------------|---------|
| Fichiers | snake_case | `character_service.py` |
| Classes | PascalCase | `LinkService` |
| Fonctions | snake_case | `get_user_characters()` |
| Constants | SCREAMING_SNAKE | `MAX_THEME_CARDS` |
| Booléens | préfixe `is_`, `has_`, `can_` | `is_published`, `has_owner` |

### Size limits

- Function : max **50 lines** (ideally < 20) — split if more
- File : max **500 lines** — extract module if more
- Parameters : max **5** per function — use dataclass if more
- Indentation : max **3 levels** — extract function if more

### Type hints

- Required on all public functions and methods
- `mypy --strict` must pass before commit

### Comments

- Explain WHY, never WHAT
- Docstring required on all public functions and classes
- No commented-out code — delete it
- TODOs must be converted to GitHub issues before merge

### Error handling

- Use domain-specific exceptions (`CharacterNotFoundError`, not `Exception`)
- Handle errors at the level that has context to treat them
- No bare `except: pass` or generic `except Exception`

## Database Rules

- All models inherit from `BaseModel` (UUID PK, `created_at`, `updated_at`)
- Federable models inherit from `ActivityPubMixin` (`ap_id`, `inbox`, `outbox`, `local`)
- `status` is indexed on Character, Report, Follow, LinkRequest
- Federated content is never deleted — use `deleted_at` + `ActiveManager`
- `select_related`/`prefetch_related` required on all paginated querysets
- Max 10 SQL queries per page — verify with `django-debug-toolbar` in dev

## Security Rules

- All external data (remote instances, user input) validated before use
- No secrets in code — only via environment variables
- HTTP Signatures verified before processing any ActivityPub activity
- SQL queries only via ORM — no `.raw()` without review

## Test Priorities (70/20/10)

- **70%** — Static analysis: `mypy --strict`, `ruff check` pass
- **20%** — Contract tests: Claim/Adopt/Fork, HTTP signatures, Character status transitions
- **10%** — E2E tests: report publication and Adopt flow only

### What to test

- Business logic that can be wrong (services, validators)
- Edge cases and expected errors (NPC already claimed, expired signature…)
- State transitions: NPC → CLAIMED / ADOPTED / FORKED
- Cryptographic signatures: valid, invalid, expired, missing header

### What NOT to test

- Django framework (ORM, auth, admin)
- CRUD views without custom logic
- Template rendering
- Migrations

## Federation Rules

- HTTP Signatures verified on ALL incoming activities, no exceptions
- Each activity handler is idempotent
- Unknown incoming activities are silently ignored (never rejected with error)
- Outgoing activity delivery is always async (never in request/response)
- Rate limiting on outgoing sends to avoid spamming remote inboxes
