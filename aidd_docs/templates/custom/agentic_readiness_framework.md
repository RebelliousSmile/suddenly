---
name: agentic-readiness-framework
description: Evaluation grid for AI-compatible project architecture.
---

# Agentic Readiness Framework

> Based on "AI Is Forcing Us To Write Good Code" — Logic.inc (Dec. 2025)

## Actionable rules

Principles are encoded as challengeable rules in `.claude/rules/custom/*-agentic-*.md`. During the audit, each rule is challenged against the project's actual stack.

## Core principle

AI agents amplify codebase quality — good or bad. Every decision below answers:
**does this choice reduce or increase the decision space left to the agent?**

---

## The 4 foundational principles

### 1. Tests

100% coverage is an agent control mechanism, not a quality target. Any uncovered line necessarily comes from what the agent just wrote. Coverage measures execution, not correctness — pair with meaningful assertions.

> Constraints → `*-agentic-tests.md`

### 2. Typing

The type checker is the agent's first guardrail. Without strict typing, the agent infers constraints from narrative context — a source of silent errors.

> Constraints → `*-agentic-type-safety.md`

### 3. Tooling

Every manual check is a decision delegated back to the agent. A single command must verify everything.

> Constraints → `*-agentic-tooling.md`

### 4. Agent context

Without explicit context, the agent infers conventions from the codebase. `CLAUDE.md` + scoped rules files is the highest-ROI investment.

---

## Rules quality rubric

Each rules file is evaluated on:

| Axis | ✅ | ❌ |
|------|----|----|
| Scoping | Scoped to paths via `paths:` frontmatter | Global but should be scoped |
| Actionability | Constrains a specific decision | Descriptive prose (test: can the agent violate it unknowingly?) |
| Coverage | Every critical module has at least one scoped rule | No rules cover any module |
| Coherence | Consistent with CLAUDE.md and other rules | Contradictions detected |

Audit output per file: `Scoping / Actionability / Coverage gap / Contradiction`
Then: coverage score, actionable vs descriptive count, gaps list for `/generate_rules`.

---

## Decision tables

### Language and framework

| Context | Recommended |
|---------|------------|
| New backend | TypeScript / Node.js or Bun |
| Frontend / fullstack | TypeScript strict + framework static analysis |
| PrestaShop module | PHP 8.x + PHPStan level 8 |
| Script / internal tool | Python 3.10+ + Mypy strict |
| CLI tool | Rust (less mature agentic ecosystem — justify need) |

### Tests

| Need | Recommended | Alternative | ❌ Signal |
|------|------------|-------------|----------|
| JS/TS | Vitest | Jest | No tests or coverage |
| PHP | PHPUnit | Pest | Manual tests only |
| API mocking | fast-forward | MSW | Real network calls in unit tests |
| Python | pytest | unittest | No coverage enforcement |

### Typing and code quality

| Need | Recommended | Alternative | ❌ Signal |
|------|------------|-------------|----------|
| Python | Mypy strict | Pyright | No static analysis |
| JS/TS | Biome | ESLint + Prettier | No linter |
| PHP | PHPStan level 8 | Psalm | Level < 5 or absent |
| Python | Ruff | Flake8 + Black | No linter |

### ORM (TypeScript)

| Context | Recommended |
|---------|------------|
| Teams / handoff | Prisma |
| Edge / Nuxt | Drizzle |
| Complex SQL | Kysely |

### CI/CD

A CI that does not block merge is worse than no CI — false sense of security.

| Need | Recommended | ❌ Signal |
|------|------------|----------|
| Pipeline | GitHub Actions / GitLab CI | CI not blocking merge |
| Lint in CI | Check mode (not auto-fix) | Formatting unchecked |
| Coverage | Enforced thresholds | Threshold at 0% |

---

## Tech selection — weighted alternatives

Score 3 candidates per component on two axes:

| Axis | Scale | Definition |
|------|-------|------------|
| **LLM coverage** | 1–3 | Training data representation, API stability |
| **Human supervision** | 1–3 | Human's ability to review and correct agent output in this tech |

**Human supervision** cannot be inferred from codebase presence alone — a project bootstrapped from a reference (BookWyrm, template, AI scaffold) contains code the human may not be able to supervise. When uncertain, **ask the human** to self-assess per component:

| Score | Meaning |
|-------|---------|
| 3 | Human can spot and fix agent errors in this tech without research |
| 2 | Human understands the concepts but needs docs to verify details |
| 1 | Human cannot reliably review agent output in this tech |

**Combined** = LLM × 0.6 + Sup × 0.4

**LLM floor rule**: if recommended option has LLM ≥ 1 below best alternative → flag deviation, require human confirmation.

**Coherence pass**: no inter-component friction, stack consistent with project needs.

---

## Investment prioritization

### Priority 1 — Low cost, immediate impact
- Install linter with pre-commit hook (< 1h)
- Create/improve `CLAUDE.md` with check command and constraints (< 1h)
- Coverage 100% on new files only from day one

### Priority 2 — Medium cost, feedback loop
- Mock external API calls in unit tests
- OpenAPI spec for main endpoints (if applicable)
- Expand coverage to existing files (start with business logic)

### Priority 3 — High cost, structural
- Static analysis: activate incrementally (baseline → increase level)
- ORM migration: new modules first, not global rewrite
- Semantic types: module by module for business IDs

---

## Branching

A merge conflict resolved by the agent without context is a source of silent errors.

| Context | Strategy |
|---------|---------|
| Parallel features | Separate branches + frequent rebase |
| Dependent sub-tasks | Parent branch + child sub-branches |
| Hotfix during agentic work | Hotfix from `main`, rebase all active branches |
| Merge conflict | Agent stops, human resolves |

> Constraints → `*-agentic-branching.md`

---

*Sources: [AI Is Forcing Us To Write Good Code](https://bits.logic.inc/p/ai-is-forcing-us-to-write-good-code) · [fast-forward](https://github.com/with-logic/fast-forward)*
