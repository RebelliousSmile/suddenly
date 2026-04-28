# Import & Export

Suddenly lets you export your games and characters as JSON files for **backup** or **instance migration**. These files can be re-imported on any Suddenly instance.

!!! info "Reports are not included"
    Reports (comptes-rendus) are federated via ActivityPub and available through subscriptions — they are not part of the personal data export.

---

## Games — `suddenly-games.json`

### Export

Go to **Settings → Data** and click **Download my games (JSON)**.

Only local games you own are included (`remote=false`).

### Format

```json
[
  {
    "title": "City of Mist — Season 2",
    "created_at": "2024-03-15T10:00:00+00:00",
    "description": "Urban fantasy noir campaign set in a city of living myths.",
    "game_system": "City of Mist",
    "is_public": true
  },
  {
    "title": "Ironsworn: Starforged",
    "created_at": "2024-07-01T08:30:00+00:00",
    "description": "",
    "game_system": "Starforged",
    "is_public": false
  }
]
```

### Fields

| Field | Type | Required | Notes |
|-------|------|:--------:|-------|
| `title` | string | ✅ | Max 200 characters |
| `created_at` | ISO 8601 datetime | ✅ | Used for deduplication — do not alter |
| `description` | string | — | Defaults to `""` if omitted |
| `game_system` | string | — | Max 100 characters. Defaults to `""` if omitted |
| `is_public` | boolean | — | Defaults to `true` if omitted |

### Import rules

- Items without `title` are **skipped**
- Items without `created_at` are **created** without deduplication check
- If a game with the same `(title, created_at)` already exists → **skipped** (idempotent)
- Otherwise → created with a new UUID; the original `created_at` is preserved
- Unknown fields are **ignored silently**

---

## Characters — `suddenly-characters.json`

### Export

Go to **Settings → Data** and click **Download my characters (JSON)**.

All characters where you are the **creator** are exported, regardless of their current status (NPC, PC, claimed, adopted, forked).

### Format

```json
[
  {
    "name": "Vasquez",
    "origin_game_title": "City of Mist — Season 2",
    "created_at": "2024-03-20T14:30:00+00:00",
    "description": "Former detective, now private investigator in the Mist.",
    "status": "npc",
    "sheet_url": null
  },
  {
    "name": "The Archivist",
    "origin_game_title": "City of Mist — Season 2",
    "created_at": "2024-04-10T09:15:00+00:00",
    "description": "Keeper of forbidden maps. Speaks only in riddles.",
    "status": "adopted",
    "sheet_url": "https://docs.google.com/spreadsheets/d/..."
  }
]
```

### Fields

| Field | Type | Required | Notes |
|-------|------|:--------:|-------|
| `name` | string | ✅ | Max 100 characters |
| `origin_game_title` | string | ✅ | Must exactly match the `title` of a game owned by the importing user |
| `created_at` | ISO 8601 datetime | ✅ | Used for deduplication — do not alter |
| `description` | string | — | Defaults to `""` if omitted |
| `status` | string | — | One of: `npc` `pc` `claimed` `adopted` `forked`. Defaults to `npc` |
| `sheet_url` | string (URL) | — | Defaults to `null` if omitted |

### Import rules

- Items without `name` are **skipped**
- `origin_game_title` must exactly match (case-sensitive) a game owned by the importing user → **skipped** if not found
- If a character with the same `(name, created_at)` already exists → **skipped** (idempotent)
- Otherwise → created with a new UUID and auto-generated slug; the original `created_at` is preserved
- `owner` is set to the importing user only when `status` is `pc`
- Unknown fields are **ignored silently**

---

## Migration workflow

When moving your account to another instance:

!!! warning "Order matters"
    Always import **games first**, then characters. Characters reference a game by title — if the game doesn't exist yet on the new instance, the character will be skipped.

```
1. Settings → Data → Download my games (JSON)
2. Settings → Data → Download my characters (JSON)
3. On the new instance: import games
4. On the new instance: import characters
```

Follows use the Mastodon-compatible CSV format (separate flow, also in Settings → Data).

---

## Creating files programmatically

Both formats are plain JSON arrays. You can generate them from any tool or script as long as you respect the required fields and the ISO 8601 datetime format with timezone offset.

**Minimal valid games file:**

```json
[{ "title": "My Campaign", "created_at": "2025-01-01T00:00:00+00:00" }]
```

**Minimal valid characters file:**

```json
[{
  "name": "My Character",
  "origin_game_title": "My Campaign",
  "created_at": "2025-01-02T00:00:00+00:00"
}]
```

!!! tip "Timezone"
    Use UTC (`+00:00`) whenever possible. Datetimes without a timezone offset may cause deduplication to behave unexpectedly.
