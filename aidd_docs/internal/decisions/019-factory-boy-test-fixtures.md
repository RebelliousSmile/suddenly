# Decision: factory-boy for test data generation

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-019        |
| Date    | 2026-03-06     |
| Feature | Testing        |
| Status  | Accepted       |

## Context

`factory-boy` is installed but unused. All test data is created via manual fixtures in `conftest.py` with hardcoded values, making it difficult to create variants or batch data.

## Decision

Adopt factory-boy factories as the primary test data generation method. Migrate existing manual fixtures to use factories.

### Factory location

- `tests/factories.py` — all factories in one file
- Fixtures in `conftest.py` delegate to factories

### Required factories (MVP)

- `UserFactory` — local user with auto-generated username/email
- `GameFactory` — game with owner
- `CharacterFactory` — NPC character with creator and origin game
- `ReportFactory` — report with author and game

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Keep manual fixtures | No learning curve | Hardcoded values, no batch, no variants | Doesn't scale |
| Model Bakery | Simpler API | Less control, less popular | factory-boy already installed |

## Consequences

- Test data is dynamic and composable (`UserFactory(bio="custom")`, `create_batch(10)`)
- `conftest.py` fixtures become thin wrappers around factories
- Existing tests continue to work unchanged (fixtures return same objects)
