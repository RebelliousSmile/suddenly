# Architecture

## Language/Framework

```text
@requirements.txt
```

```mermaid
flowchart LR
    subgraph "Framework"
        Django["Django (SSR)"]
        DRF["Django REST Framework"]
        Allauth["django-allauth"]
        HTMX["django-htmx"]
    end
    subgraph "Federation"
        AP["ActivityPub (custom)"]
        Sig["HTTP Signatures (cryptography)"]
        HTTPX["httpx"]
        RL["django-ratelimit"]
    end
    subgraph "Data"
        PG["PostgreSQL"]
        Celery["Celery + django-celery-beat"]
        Redis["Redis (optional)"]
    end
    subgraph "API & Docs"
        Spectacular["drf-spectacular (OpenAPI)"]
    end
    Django --> DRF
    Django --> Allauth
    Django --> HTMX
    DRF --> Spectacular
    Django --> AP
    AP --> Sig
    AP --> HTTPX
    Django --> PG
    Django --> Celery
    Celery --> Redis
```

### Naming Conventions

- **Files**: snake_case (`character_service.py`)
- **Classes**: PascalCase (`LinkService`)
- **Functions**: snake_case (`get_user_characters()`)
- **Constants**: SCREAMING_SNAKE (`MAX_THEME_CARDS`)

## Deployment Philosophy

- Django standard app — runs anywhere Python + PostgreSQL are available
- Docker is optional, not required
- Small instance (< 50 users): Django + PostgreSQL only
- Medium (50–500): + Redis recommended
- Large (500+): + Celery for federation delivery

### Dependency Matrix

| Component | Required | Optional | Fallback |
|-----------|----------|----------|---------|
| Python 3.12+ | ✅ | — | — |
| PostgreSQL | ✅ | — | — |
| Redis | — | ✅ | DB cache |
| Celery | — | ✅ | Sync tasks |

## Frontend

- HTMX + Alpine.js + UnoCSS (Vite build)
- No SPA, SSR with Vite for asset bundling
- Total bundle: ~32KB (HTMX 14KB + Alpine 8KB + UnoCSS ~10KB purged)

## Tooling & Quality Gates

- **Unified check**: `make check` runs lint + typecheck + tests + coverage
- **Lint**: Ruff (E, F, I, N, W, UP rules)
- **Type check**: mypy strict + django-stubs
- **Coverage**: pytest-cov, fail_under=80%
- **Pre-commit**: ruff (with --fix) + mypy
- **CI**: GitHub Actions — ruff check + mypy + pytest --cov, blocks merge on failure
- **CI database**: PostgreSQL 16 service container for Django test DB

## Security Patterns

### HTTP Signatures
- All outgoing AP requests signed with RSA-SHA256
- Headers signed: `(request-target) host date digest`
- Implemented in `suddenly/activitypub/signatures.py`

### Rate Limiting
- Inbox: 100/h — API: 1000/h — Auth: 10/min
- Simple: Django middleware; Production: Redis + django-ratelimit

## Services communication

### Request flow

```mermaid
C4Context
    title Services Communication — Suddenly
    Person(browser, "Browser", "HTMX partial or full page")
    Person(remote, "Remote Instance", "ActivityPub peer")
    System(django, "Django App", "Views + DRF ViewSets + AP endpoints")
    SystemDb(pg, "PostgreSQL", "Primary datastore")
    System(celery, "Celery Worker", "Async AP delivery, cleanup tasks")
    SystemDb(redis, "Redis", "Optional broker + cache")

    Rel(browser, django, "HTTP (HTMX, JSON)")
    Rel(remote, django, "ActivityPub (POST inbox)")
    Rel(django, pg, "ORM queries")
    Rel(django, celery, "Enqueue tasks")
    Rel(celery, redis, "Broker (optional)")
    Rel(celery, pg, "DB cache fallback")
```

### External Services

#### ActivityPub peers

- Remote instances receive activities via HTTP POST to their inbox
- Actor discovery via WebFinger (`/.well-known/webfinger`)
- Instance metadata via NodeInfo (`/.well-known/nodeinfo`)
- HTTP Signatures for request authenticity

#### Redis (optional)

- Celery broker + result backend
- Cache backend
- Fallback: DB cache + synchronous task execution (`CELERY_TASK_ALWAYS_EAGER=True`)

#### PostgreSQL

- Primary database (FTS, JSON fields)
- DB cache fallback when Redis absent
