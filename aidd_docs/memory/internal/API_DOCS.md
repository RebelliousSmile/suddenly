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

### ActivityPub (`application/activity+json`)

**Actors**: User (Person), Character (Person), Game (Group)

| Actor | Endpoints |
|-------|-----------|
| User | `GET /users/{username}` · `POST /users/{username}/inbox` · `GET /users/{username}/outbox` · `GET /users/{username}/followers` |
| Game | `GET /games/{id}` · `POST /games/{id}/inbox` · `GET /games/{id}/outbox` |
| Character | `GET /characters/{id}` · `POST /characters/{id}/inbox` · `GET /characters/{id}/outbox` |

**Global endpoints**:

| Endpoint | Usage |
|----------|-------|
| `GET /.well-known/webfinger?resource=acct:user@domain` | Actor discovery |
| `GET /.well-known/nodeinfo` | NodeInfo index |
| `GET /nodeinfo/2.0` | Instance details |
| `POST /inbox` | Shared inbox |

### Feed (`/feed/`)

- `GET /feed/` — personal feed (authenticated)
- `GET /feed/instance/` — local instance feed
- `GET /feed/fediverse/` — federated feed
- `POST /feed/recommend/` — recommend a report

### Notifications (`/notifications/`)

- `GET /notifications/` — notification list
- `POST /notifications/mark-all-read/` — mark all as read
- `GET /notifications/badge/` — HTMX badge count (polling)

### Onboarding (`/welcome/`)

- `GET /welcome/` — onboarding step 1
- `GET /welcome/discover/` — onboarding step 2
- `GET /welcome/start/` — onboarding step 3

### Admin panel (`/gmh/`, requires `is_admin`)

- `GET /gmh/` — admin dashboard
- `GET /gmh/instances/` — federated instances list
- `POST /gmh/instances/{pk}/block/` — block an instance
- `POST /gmh/instances/{pk}/unblock/` — unblock an instance
- `GET /gmh/users/` — user list
- `POST /gmh/users/{pk}/suspend/` — suspend a user
- `GET /gmh/settings/` — instance settings

### Other

- `GET /health/` — `{"status": "ok"}`
- `/admin/` — Django admin
- `/accounts/` — django-allauth
- `GET /@{username}` — user profile page

## Request/Response Formats

- REST: `Content-Type: application/json`
- ActivityPub: `Content-Type: application/activity+json`
- Paginated: `{ count, next, previous, results[] }`
- Errors: `{ detail }` or `{ field: [errors] }`

## Supported ActivityPub Activities

| Activity | Actor | Object | Usage |
|----------|-------|--------|-------|
| Follow | User | User/Character/Game | Follow |
| Accept | User | Follow/Offer | Accept |
| Reject | User | Follow/Offer | Reject |
| Create | User | Report/Quote/Character | Publish |
| Update | User | Report/Quote/Character | Edit |
| Delete | User | Report/Quote | Delete |
| Announce | User | Report | Share |
| Offer | User | Claim/Adopt/Fork | Propose link |

## Suddenly Namespace

- ActivityPub extensions: `https://suddenly.social/ns#`

| Property | Description |
|----------|-------------|
| `suddenly:status` | Character status (NPC/PC/CLAIMED/ADOPTED) |
| `suddenly:originGame` | Character's origin game |
| `suddenly:creator` | Original creator |
| `suddenly:appearances` | Appearances in reports |
| `suddenly:quotes` | Character quotes |
| `suddenly:links` | Claim/Adopt/Fork links |
| `suddenly:gameSystem` | Game system |
| `suddenly:targetCharacter` | Target NPC (for Offer) |
| `suddenly:proposedCharacter` | Proposed PC (for Claim) |
| `suddenly:relationship` | Relationship type (for Fork) |

## HTTP Signatures

- All POST requests to inboxes are signed

```
headers: (request-target) host date digest
algorithm: rsa-sha256
keyId: https://instance/actor#main-key
```

- Verification: fetch `publicKey.publicKeyPem` from actor, reconstruct signature string, verify RSA-SHA256

## Mastodon Compatibility

| Suddenly Type | Displayed as |
|---------------|--------------|
| Report (Article) | Article |
| Quote (Note) | Note |
| Character (Person) | Person |
| Offer(Claim/Adopt/Fork) | Not sent to non-Suddenly instances |
