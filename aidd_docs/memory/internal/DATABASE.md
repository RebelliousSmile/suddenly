# Database

- **DB**: PostgreSQL (psycopg3)
- **ORM**: Django ORM
- **Connection**: `DATABASE_URL` env var in production

```mermaid
flowchart LR
    subgraph "ORM"
        Django["Django ORM"]
    end
    subgraph "Storage"
        PG["PostgreSQL"]
        Migration["Django Migrations"]
    end
    Django --> PG
    Migration --> PG
```

## Main entities and relationships

- `User` owns `Game`s, creates/owns `Character`s, authors `Report`s
- `Game` has many `Report`s and `Character`s (via `origin_game`)
- `Character` has `Quote`s, `CharacterAppearance`s, receives `LinkRequest`s
- `LinkRequest` → accepted → creates `CharacterLink` + `SharedSequence`
- `Follow` is polymorphic (targets `User`, `Character`, or `Game` via `GenericForeignKey`)

```mermaid
erDiagram
    User ||--o{ Game : owns
    User ||--o{ Report : authors
    User ||--o{ Character : "creates/owns"
    Game ||--o{ Report : has
    Game ||--o{ Character : "origin_game"
    Character ||--o{ Quote : has
    Character ||--o{ CharacterAppearance : appears_in
    Report ||--o{ CharacterAppearance : features
    Report ||--o{ ReportCast : planned_via
    Character ||--o{ LinkRequest : receives
    User ||--o{ LinkRequest : makes
    LinkRequest ||--o| CharacterLink : "accepted into"
    CharacterLink ||--|| SharedSequence : creates
    FederatedServer }o--o{ User : "remote actors"
```

## Migrations

Django migrations — `python manage.py migrate`

- Apps with migrations: `users`, `games`, `characters`, `activitypub`
- All models use UUID primary keys

## Seeding

No seeding strategy defined yet.
