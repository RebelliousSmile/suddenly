# Agentic test practices

> Source: Agentic Readiness Framework — Principle 1 (Tests)
> Challengeable by `/agentic_architecture` after stack definition.

- Coverage threshold enforced at 80% globally (`--cov-fail-under=80`) — aim for 100% on new and modified files
- Unit test suite must complete in < 60s — a slow suite discourages the agent from running tests after every change
- Unit tests must not depend on network or external APIs — mock or cache all external calls
- Django test DB is allowed (pytest-django fixtures) — but no production DB or external services
- No test file without meaningful assertions — execution is not correctness
- Coverage threshold must be enforced (not just measured) — an unenforced metric gives the agent no signal
