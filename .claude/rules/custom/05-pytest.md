---
paths:
  - "tests/**/*.py"
  - "**/test_*.py"
---

# Pytest conventions

## Fixtures & factories

- Use factory-boy factories, not manual object creation
- Shared fixtures in `conftest.py`, not duplicated across files
- Prefer `pytest.fixture` over `setUp` / `tearDown`

## Assertions

- Every test must assert something meaningful — no test without assertions
- Use `pytest.raises` for expected exceptions
- One behavior per test function

## Mocking

- Use `pytest-mock` (`mocker` fixture), not `unittest.mock` directly
- Mock external calls (HTTP, Celery tasks) — never hit network in tests
- Django test DB is allowed — no need to mock ORM
