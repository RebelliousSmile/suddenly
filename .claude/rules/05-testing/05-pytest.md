---
paths:
  - "tests/**/*.py"
  - "**/test_*.py"
---

# Pytest conventions

## Fixtures & factories

- Use factory-boy factories, not manual object creation
- All factories in `tests/factories.py`
- Shared fixtures in `conftest.py` delegate to factories, not duplicated across files
- Prefer `pytest.fixture` over `setUp` / `tearDown`

## Assertions

- Every test must assert something meaningful — no test without assertions
- Use `pytest.raises` for expected exceptions
- One behavior per test function

## E2E tests (Playwright)

- Mark E2E tests with `@pytest.mark.e2e`
- Run separately: `pytest tests/ -m e2e`
- E2E tests use `pytest-playwright` — browser-based user journeys
- Keep E2E tests focused on critical paths, not edge cases

## Mocking

- Use `pytest-mock` (`mocker` fixture), not `unittest.mock` directly
- Mock external calls (HTTP, Celery tasks) — never hit network in tests
- Django test DB is allowed — no need to mock ORM
