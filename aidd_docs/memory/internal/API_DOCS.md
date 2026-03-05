# API Documentation

## Authentication & Authorization

- **Authentication**: Session (`SessionAuthentication`)
- **Authorization**: `IsAuthenticatedOrReadOnly` — reads public, writes require login
- **ActivityPub**: HTTP Signatures for federated requests
- **Pagination**: `PageNumberPagination`, `PAGE_SIZE=20`
- **Schema**: `/api/schema/` — Swagger: `/api/docs/` — ReDoc: `/api/redoc/`

## Endpoints

### REST API (`/api/`)

- `GET/POST /api/games/` — list / create games
- `GET/PUT/PATCH/DELETE /api/games/{id}/` — game detail
- `GET /api/characters/` — list characters (filterable: `?available=true`)
- `GET /api/characters/search/?q=` — full-text search
- `GET/PUT/PATCH/DELETE /api/characters/{id}/` — character detail
- `POST /api/characters/{id}/claim/` — create claim request
- `POST /api/characters/{id}/adopt/` — create adopt request
- `POST /api/characters/{id}/fork/` — create fork request
- `POST /api/link-requests/{id}/accept/` — accept (character creator only)
- `POST /api/link-requests/{id}/reject/` — reject (character creator only)
- `GET/POST /api/reports/` — list / create reports
- `POST /api/reports/{id}/publish/` — publish draft report

### ActivityPub (non-DRF, `application/activity+json`)

- `GET /.well-known/webfinger?resource=acct:user@domain`
- `GET /.well-known/nodeinfo` — NodeInfo index
- `GET /.well-known/nodeinfo/2.0` — NodeInfo 2.0
- `GET /users/{username}` — User actor (Person)
- `POST /users/{username}/inbox` — receive activities
- `GET /users/{username}/outbox` — published reports
- `GET /users/{username}/followers` — followers collection
- `GET /games/{id}` — Game actor (Collection)
- `POST /games/{id}/inbox`
- `GET /games/{id}/outbox`
- `GET /characters/{id}` — Character actor (Person)
- `POST /characters/{id}/inbox`
- `GET /characters/{id}/outbox` — public quotes

### Other

- `GET /health/` — `{"status": "ok"}`
- `/admin/` — Django admin
- `/accounts/` — django-allauth auth
- `GET /@{username}` — user profile page

## Request/Response Formats

- REST: `Content-Type: application/json`
- ActivityPub: `Content-Type: application/activity+json`
- Paginated: `{ count, next, previous, results[] }`
- Errors: `{ detail }` or `{ field: [errors] }`
