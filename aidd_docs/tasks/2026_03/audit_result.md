# Agentic Readiness Audit — Suddenly

## Project needs analysis

- **Domain**: Federated TTRPG fiction network (ActivityPub)
- **Stack**: Django 5.x / Python 3.12 / PostgreSQL / Celery+Redis (optional)
- **Codebase**: 58 source files, ~4800 LOC, 5 Django apps, services layer present
- **Constraints**: PaaS-friendly (no Docker required), BookWyrm-inspired AP implementation, HTMX+Alpine.js frontend (no SPA)
- **Not greenfield**: stack is established, code exists

## Global score

**Total: 7/15 — Basic**

## Scores by axis

### Tests

| Criterion | Score | Justification |
|-----------|-------|---------------|
| Test framework configured | ✅ | pytest 8.0 + pytest-django + factory-boy, 7 test files (1637 LOC) |
| Coverage enforced in CI | ❌ | pytest-cov installed but no thresholds configured, no CI pipeline |
| Suite fast enough to run after every change | ✅ | ~4800 LOC codebase, suite likely < 60s (needs benchmark) |
| External calls mocked | ✅ | pytest-mock installed, no live API calls in tests |
| **Score** | **3/4** | |

### Type safety

| Criterion | Score | Justification |
|-----------|-------|---------------|
| Type checker configured and enforced in CI | ❌ | mypy configured in pyproject.toml but no CI to enforce |
| Strict mode enabled | ✅ | `strict = true` in pyproject.toml, django-stubs plugin |
| No bare primitive IDs | ✅ | UUID PKs throughout, typed with Django's UUIDField |
| DB/API types inferred or annotated | ✅ | Django ORM + django-stubs provides type inference |
| **Score** | **3/4** | |

### Tooling

| Criterion | Score | Justification |
|-----------|-------|---------------|
| Unified `check` command | ❌ | No Makefile, no scripts — separate `ruff`, `mypy`, `pytest` commands |
| Lint/format tool configured | ✅ | Ruff configured (E, F, I, N, W, UP rules) |
| Pre-commit hook enforces lint | ❌ | No `.pre-commit-config.yaml` |
| CI blocks merge on failure | ❌ | No CI pipeline exists |
| **Score** | **1/4** | |

### Agent context

| Criterion | Score | Justification |
|-----------|-------|---------------|
| `CLAUDE.md` documents check command and constraints | ✅ | CLAUDE.md exists with stack, conventions, commit rules, doc pointers |
| Architectural boundaries explicit | ✅ | Memory bank documents app dependencies, critical modules, import rules |
| Rules files scoped to relevant paths | ❌ | 11 rules files exist but none use `paths:` frontmatter — all global |
| **Score** | **2/3** | |

## Human supervision self-assessment

| Component | Score | Assessment |
|-----------|-------|------------|
| Language (Python) | 1 | Cannot reliably review agent output |
| Framework (Django) | 2 | Understands concepts, needs docs to verify |
| Database (PostgreSQL) | 3 | Can spot and fix errors without research |
| ORM (Django ORM) | 2 | Understands concepts, needs docs to verify |
| Tooling (Ruff + Mypy) | 1 | Cannot reliably review agent output |
| CI (GitHub Actions) | 2 | Understands concepts, needs docs to verify |
| Tests (pytest) | 1 | Cannot reliably review agent output |
| ActivityPub / HTTP Signatures | 2 | Understands concepts, needs docs to verify |
| Celery / Redis | 1 | Cannot reliably review agent output |

## Stack alternatives

| Component | Option | LLM | Sup | Combined | Recommended |
|-----------|--------|-----|-----|----------|-------------|
| Language | Python 3.12 | 3 | 1 | 2.2 | ✅ |
| | TypeScript/Node | 3 | 1 | 2.2 | |
| | Go | 2 | 1 | 1.6 | |
| Framework | Django 5.x | 3 | 2 | 2.6 | ✅ |
| | FastAPI | 3 | 1 | 2.2 | |
| | Flask | 2 | 1 | 1.6 | |
| Database | PostgreSQL | 3 | 3 | 3.0 | ✅ |
| | SQLite | 2 | 3 | 2.4 | |
| | MySQL | 2 | 3 | 2.4 | |
| ORM | Django ORM | 3 | 2 | 2.6 | ✅ |
| | SQLAlchemy | 3 | 1 | 2.2 | |
| | Tortoise ORM | 1 | 1 | 1.0 | |
| Tooling | Ruff + Mypy | 3 | 1 | 2.2 | ✅ |
| | Flake8 + Black + Mypy | 2 | 1 | 1.6 | |
| | Pyright + Ruff | 2 | 1 | 1.6 | |
| CI | GitHub Actions | 3 | 2 | 2.6 | ✅ |
| | GitLab CI | 2 | 2 | 2.0 | |
| | CircleCI | 2 | 2 | 2.0 | |
| Tests | pytest | 3 | 1 | 2.2 | ✅ |
| | unittest | 2 | 1 | 1.6 | |
| | ward | 1 | 1 | 1.0 | |

## Deviations

None. Current stack still scores highest Combined per component — but the low supervision scores (Python 1, Ruff+Mypy 1, pytest 1, Celery 1) reveal a critical pattern: **the human cannot reliably review agent output on 4/9 core technologies**. This makes automated guardrails (CI, coverage, strict types) not just nice-to-have but essential compensating controls. Without them, agent errors in Python code, test quality, and tooling config will go undetected.

**Implication**: Priority 1-2 actions (CI pipeline, coverage enforcement, pre-commit hooks) become **blockers**, not improvements — they replace human supervision that is absent.

## Coherence check

| Check | Result | Notes |
|-------|--------|-------|
| No inter-component friction | ✅ | Django+PostgreSQL+pytest+Ruff+Mypy is a mature, well-integrated stack |
| Stack consistent with project needs | ✅ | ActivityPub requires httpx+cryptography (present), Django ecosystem has BookWyrm as reference |

## Rules challenge

| Rule file | Verdict | Detail |
|-----------|---------|--------|
| `04-agentic-tooling.md` | Applies as-is | Single check command needed (Makefile or script). CI blocks merge needed (GitHub Actions). |
| `06-agentic-tests.md` | Needs adaptation | "No DB dependency" conflicts with Django test reality — Django tests use test DB. Adapt: allow Django test DB, enforce no external network calls. |
| `07-agentic-type-safety.md` | Applies as-is | mypy strict already enabled. "No bare primitives for IDs" met with UUID fields. |
| `08-agentic-branching.md` | Applies as-is | Single developer for now, but rules prepare for multi-agent work. |

## Rules quality audit

| File | Scoping | Actionability | Coverage gap | Contradiction |
|------|---------|---------------|-------------|---------------|
| `01-standards/1-command-structure.md` | ⚠️ global (cross-cutting) | ✅ constrains decisions | — | — |
| `01-standards/1-mermaid.md` | ⚠️ global (cross-cutting) | ✅ constrains decisions | — | — |
| `01-standards/1-rule-structure.md` | ✅ scoped to `.claude/rules/` | ✅ constrains decisions | — | — |
| `01-standards/1-rule-writing.md` | ✅ scoped to `.claude/rules/` | ✅ constrains decisions | — | — |
| `04-tooling/ide-mapping.md` | ⚠️ global (cross-cutting) | ✅ constrains decisions | — | — |
| `custom/04-agentic-tooling.md` | ⚠️ global (cross-cutting) | ✅ constrains decisions | — | — |
| `custom/04-git-main-protection.md` | ⚠️ global (cross-cutting) | ✅ constrains decisions | — | — |
| `custom/06-agentic-tests.md` | ⚠️ global (cross-cutting) | ✅ constrains decisions | Django test DB | — |
| `custom/07-agentic-type-safety.md` | ⚠️ global (cross-cutting) | ✅ constrains decisions | — | — |
| `custom/08-agentic-branching.md` | ⚠️ global (cross-cutting) | ✅ constrains decisions | — | — |
| `custom/09-aidd-workflow.md` | ⚠️ global (cross-cutting) | ✅ constrains decisions | — | — |

- Rules coverage: **0/5 critical modules** have scoped rules (users, games, characters, activitypub, core)
- Actionable: 11/11 — Descriptive: 0/11
- Gaps: no rules scoped to `suddenly/activitypub/` (federation, signatures), `suddenly/characters/services.py` (business logic), `suddenly/games/` (reports)

## Prioritized actions

> With human supervision at 1 on Python/pytest/Ruff+Mypy/Celery, automated guardrails are **compensating controls** — they replace absent human review.

| Priority | Action | Axis | Cost | Why critical |
|----------|--------|------|------|-------------|
| 1 | Create unified check command (Makefile: `ruff check` + `mypy --strict` + `pytest --cov`) | Tooling | low | Agent needs one command, human needs one gate |
| 1 | Add `.pre-commit-config.yaml` with ruff + mypy | Tooling | low | Catches errors before commit since human can't review Python |
| 1 | Configure coverage thresholds in pyproject.toml (100% on new files) | Tests | low | Human can't assess test quality — coverage forces the agent to test |
| 1 | Create GitHub Actions CI pipeline (ruff + mypy + pytest + coverage gate, blocks merge) | CI | medium | **Primary supervision mechanism** replacing human review |
| 2 | Adapt `06-agentic-tests.md` for Django test DB reality | Rules | low | Current rule conflicts with Django testing patterns |
| 2 | Add scoped rules for critical modules (activitypub, characters/services) | Agent context | medium | Compensates low supervision on ActivityPub (score 2) and Python (score 1) |
| 3 | Benchmark test suite execution time, optimize if > 60s | Tests | medium | |
