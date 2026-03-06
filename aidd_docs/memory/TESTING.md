# Testing Guidelines

## Tools and Frameworks

- `pytest` + `pytest-django` — test runner
- `pytest-cov` — coverage (threshold: 80%)
- `pytest-mock` — mocking (`mocker` fixture)
- `factory-boy` — model factories (DEC-019)
- `pytest-playwright` — E2E browser tests
- `rest_framework.test.APIClient` — DRF API testing

## Testing Strategy

- **Unit tests**: model methods, service logic (`LinkService`)
- **Integration tests**: API endpoints (DRF ViewSets)
- **Federation tests**: ActivityPub inbox/outbox, WebFinger, NodeInfo
- **E2E tests**: user journeys via Playwright (signup, profile, interactions)

## Factories (DEC-019)

All factories in `tests/factories.py`. Fixtures in `conftest.py` delegate to factories.

- `UserFactory` — local user with auto-generated username/email
- `GameFactory` — game with owner
- `CharacterFactory` — NPC with creator and origin game
- `ReportFactory` — report with author and game

Usage:
```python
# Single object with override
user = UserFactory(username="alice")

# Batch
users = UserFactory.create_batch(10)

# In fixture
@pytest.fixture
def user(db):
    return UserFactory()
```

## Test Execution Process

```bash
make check                       # lint + typecheck + tests (single command)
pytest tests/                    # All tests
pytest tests/ --cov              # With coverage
pytest tests/test_api.py -v      # Specific file
pytest tests/ -m e2e             # E2E tests only
```

Test files in `tests/`:
- `conftest.py` — shared fixtures (delegate to factories)
- `factories.py` — factory-boy factories
- `test_api.py` — API endpoints
- `test_models.py` — model tests
- `test_users.py` — user tests
- `test_activitypub.py` — AP endpoints
- `test_services.py` — `LinkService` business logic
- `test_federation.py` — federation tests

## Mocking and Stubbing

- `pytest-mock`: use `mocker` fixture
- API tests: `api_client.force_authenticate(user=user)` for auth
- Federation tests: mock external HTTP calls (httpx), never hit real instances
