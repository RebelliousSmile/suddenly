# Testing Guidelines

## Tools and Frameworks

- `pytest` + `pytest-django` — test runner
- `pytest-cov` — coverage
- `pytest-mock` — mocking (`mocker` fixture)
- `factory-boy` — model factories
- `rest_framework.test.APIClient` — DRF API testing

## Testing Strategy

- **Unit tests**: model methods, service logic (`LinkService`)
- **Integration tests**: API endpoints (DRF ViewSets)
- **Federation tests**: ActivityPub inbox/outbox, WebFinger, NodeInfo
- No E2E tests configured yet

## Test Execution Process

```bash
pytest tests/           # All tests
pytest tests/ --cov     # With coverage
pytest tests/test_api.py -v  # Specific file
```

Test files in `tests/`:
- `conftest.py` — shared fixtures
- `test_api.py` — API endpoints
- `test_models.py` — model tests
- `test_users.py` — user tests
- `test_activitypub.py` — AP endpoints
- `test_services.py` — `LinkService` business logic
- `test_federation.py` — federation tests

## Mocking and Stubbing

- `pytest-mock`: use `mocker` fixture
- API tests: `api_client.force_authenticate(user=user)` for auth
- Key fixtures: `user`, `other_user`, `game`, `character`, `pc_character`, `report`, `api_client`, `authenticated_client`
