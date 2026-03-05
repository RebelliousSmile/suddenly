# Architecture Generation Summary

## Files created or modified

| Change | Type | Path | Purpose |
|--------|------|------|---------|
| created | rule | `.claude/rules/03-frameworks-and-libraries/3-django-models.md` | Scoped conventions for Django models (UUID, select_related, no business logic) |
| created | rule | `.claude/rules/03-frameworks-and-libraries/3-django-services.md` | Scoped conventions for services layer (thin views, transaction.atomic) |
| created | rule | `.claude/rules/03-frameworks-and-libraries/3-django-views.md` | Scoped conventions for views (HTMX partials, login required, thin) |
| created | rule | `.claude/rules/08-domain/8-activitypub.md` | ActivityPub domain rules (signatures, types, inbox validation) |
| created | rule | `.claude/rules/08-domain/8-characters.md` | Characters domain rules (statuses, link types, LinkService) |
| modified | rule | `.claude/rules/custom/06-agentic-tests.md` | Adapted for Django test DB (allow pytest-django fixtures, forbid network) |
| created | tooling | `Makefile` | Unified `make check` command (lint + typecheck + test + coverage) |
| created | tooling | `.pre-commit-config.yaml` | Pre-commit hooks for ruff + mypy |
| created | tooling | `.github/workflows/ci.yml` | GitHub Actions CI pipeline (PostgreSQL, ruff, mypy, pytest, coverage gate) |
| modified | config | `pyproject.toml` | Added coverage threshold (fail_under=80) to pytest addopts |
| modified | context | `CLAUDE.md` | Updated dev commands: `make check`, individual commands, pip install editable |
| deleted | agent | `.claude/agents/custom-ada.md` | Stale agent referencing wrong project (cabinet-partage) |

## Audit signals addressed

| Signal | Solution applied |
|--------|-----------------|
| No unified check command | `Makefile` with `make check` (ruff + mypy + pytest --cov) |
| No pre-commit hook | `.pre-commit-config.yaml` with ruff + mypy |
| No coverage threshold | `pyproject.toml` fail_under=80, enforced in pytest addopts |
| No CI pipeline | `.github/workflows/ci.yml` blocks merge on lint/type/test/coverage failure |
| Rules not scoped to paths | 5 new rules with `paths:` frontmatter covering Django + domain modules |
| `06-agentic-tests` incompatible with Django | Adapted: Django test DB allowed, network calls forbidden |

## Audit signals deferred

| Signal | Reason |
|--------|--------|
| Coverage 100% on new files | Start with 80% global threshold, increase incrementally |
| Test suite benchmark < 60s | Suite likely fast enough given ~4800 LOC, benchmark after CI is running |

## Architecture decisions

- **No new agents**: existing 5 agents (alexia, iris, kent, martin, claire) cover all responsibilities
- **Deleted custom-ada**: referenced cabinet-partage.fr, not Suddenly
- **Coverage at 80%, not 100%**: existing codebase needs incremental coverage increase; 100% on new files can be a future CI step
- **CI with PostgreSQL service**: Django tests require a real test DB, consistent with adapted agentic-tests rule
- **Pre-commit with ruff --fix**: auto-fix on commit for developer convenience, CI runs in check mode

## Recommended next steps

1. Install pre-commit hooks: `pip install pre-commit && pre-commit install`
2. Run `make check` to establish baseline — fix any existing lint/type/test failures
3. Increase coverage threshold incrementally as tests are added
4. Add `pre-commit` to dev dependencies in `pyproject.toml`
