# Import / Export — Format Specification

Suddenly supports JSON-based import/export of games and characters for backup and instance migration purposes.

Reports are **not** included — they are federated via ActivityPub and available through subscriptions.

---

## Games — `suddenly-games.json`

### Export endpoint

```
GET /settings/export-games/
```

Returns a `application/json` attachment. Only local games (`remote=False`) owned by the authenticated user are included.

### Format

```json
[
  {
    "title": "City of Mist — Season 2",
    "description": "Urban fantasy noir campaign set in a city of living myths.",
    "game_system": "City of Mist",
    "is_public": true,
    "created_at": "2024-03-15T10:00:00+00:00"
  }
]
```

### Field reference

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `title` | string | **yes** | Max 200 chars |
| `created_at` | string (ISO 8601) | **yes** | Used for deduplication |
| `description` | string | no | Defaults to `""` |
| `game_system` | string | no | Max 100 chars. Defaults to `""` |
| `is_public` | boolean | no | Defaults to `true` |

### Import endpoint

```
POST /settings/import-games/
Content-Type: multipart/form-data
Field: games_file
```

### Import rules

- Items missing `title` are **skipped**
- Items missing `created_at` are **created** without deduplication check
- If a game with identical `(title, created_at)` already exists for this user → **skipped**
- Otherwise → created with a new UUID; `created_at` is set to the original value
- Unknown fields in the JSON are **ignored silently**

---

## Characters — `suddenly-characters.json`

### Export endpoint

```
GET /settings/export-characters/
```

Returns a `application/json` attachment. Only local characters (`remote=False`) where `creator == authenticated user` are included, regardless of current status (NPC, PC, claimed, adopted, forked).

### Format

```json
[
  {
    "name": "Vasquez",
    "description": "Former detective, now private investigator in the Mist.",
    "status": "npc",
    "sheet_url": "https://docs.google.com/...",
    "origin_game_title": "City of Mist — Season 2",
    "created_at": "2024-03-20T14:30:00+00:00"
  }
]
```

### Field reference

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | **yes** | Max 100 chars |
| `origin_game_title` | string | **yes** | Must match the `title` of an existing game owned by the importing user |
| `created_at` | string (ISO 8601) | **yes** | Used for deduplication |
| `description` | string | no | Defaults to `""` |
| `status` | string | no | One of: `npc`, `pc`, `claimed`, `adopted`, `forked`. Defaults to `npc` |
| `sheet_url` | string (URL) | no | Defaults to `null` |

### Import endpoint

```
POST /settings/import-characters/
Content-Type: multipart/form-data
Field: characters_file
```

### Import rules

- Items missing `name` are **skipped**
- `origin_game_title` must match (exact, case-sensitive) a game owned by the importing user → **skipped** if not found
- **Import games first** before importing characters, otherwise all characters will be skipped
- If a character with identical `(name, created_at)` already exists for this creator → **skipped**
- Otherwise → created with a new UUID; `created_at` is set to the original value; slug is auto-generated
- `owner` is set to the importing user on creation
- Unknown fields in the JSON are **ignored silently**

---

## Recommended migration workflow

When moving to another instance:

1. Export games → `suddenly-games.json`
2. Export characters → `suddenly-characters.json`
3. On the new instance: import games first
4. On the new instance: import characters

Follows/subscriptions use the [Mastodon-compatible CSV format](../external/claim-adopt-fork.md) — see the "Import follows" section in Settings > Data.
