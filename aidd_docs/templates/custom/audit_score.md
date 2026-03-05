---
name: audit-score
description: Structured output template for the agentic readiness audit. Covers project needs analysis, axis scoring, human supervision inference, stack alternatives with weighted scoring, deviations, coherence check, and prioritized actions.
---

# Agentic Readiness Audit

## Project needs analysis

> Functional and technical constraints extracted from the project (CLAUDE.md, code, docs).
> If greenfield: document human stack preferences gathered before generating alternatives.

- ...

## Global score

**Total: X/15 — Level** *(Insufficient / Basic / Intermediate / Advanced)*

## Scores by axis

### Tests

| Criterion | Score | Justification |
|-----------|-------|---------------|
| Test framework configured | ✅ / ❌ / N/A | |
| Coverage enforced in CI | ✅ / ❌ / N/A | |
| Suite fast enough to run after every change | ✅ / ❌ / N/A | |
| External calls mocked | ✅ / ❌ / N/A | |
| **Score** | **X/4** | |

### Type safety

| Criterion | Score | Justification |
|-----------|-------|---------------|
| Type checker configured and enforced in CI (mypy / pyright / tsc) | ✅ / ❌ / N/A | |
| Strict mode enabled | ✅ / ❌ / N/A | |
| No bare primitive IDs | ✅ / ❌ / N/A | |
| DB/API types inferred or annotated | ✅ / ❌ / N/A | |
| **Score** | **X/4** | |

### Tooling

| Criterion | Score | Justification |
|-----------|-------|---------------|
| Unified `check` command (typecheck + lint + tests) | ✅ / ❌ / N/A | |
| Lint/format tool configured (Biome / Ruff / other) | ✅ / ❌ / N/A | |
| Pre-commit hook enforces lint | ✅ / ❌ / N/A | |
| CI blocks merge on failure | ✅ / ❌ / N/A | |
| **Score** | **X/4** | |

### Agent context

| Criterion | Score | Justification |
|-----------|-------|---------------|
| `CLAUDE.md` documents check command and constraints | ✅ / ❌ / N/A | |
| Architectural boundaries explicit | ✅ / ❌ / N/A | |
| Rules files scoped to relevant paths | ✅ / ❌ / N/A | |
| **Score** | **X/3** | |

## Human supervision self-assessment

> Ask the human to self-assess. Do NOT infer from codebase presence alone.
> 3 = can spot and fix agent errors without research
> 2 = understands concepts, needs docs to verify details
> 1 = cannot reliably review agent output

| Component | Human self-assessment | Score (1–3) |
|-----------|----------------------|-------------|
| Language | | |
| Framework | | |
| Database | | |
| ORM | | |
| Tooling | | |
| CI | | |
| Tests | | |

## Stack alternatives

> Combined = LLM × 0.6 + Sup × 0.4. Sup is per component (same value across all options).
> Recommended = option with highest Combined score (unless deviation justified).

| Component | Option | LLM | Sup | Combined | Recommended |
|-----------|--------|-----|-----|----------|-------------|
| Language | Option A | | | | |
| | Option B | | | | |
| | Option C | | | | |
| Framework | Option A | | | | |
| | Option B | | | | |
| | Option C | | | | |
| Database | Option A | | | | |
| | Option B | | | | |
| | Option C | | | | |
| ORM | Option A | | | | |
| | Option B | | | | |
| | Option C | | | | |
| Tooling | Option A | | | | |
| | Option B | | | | |
| | Option C | | | | |
| CI | Option A | | | | |
| | Option B | | | | |
| | Option C | | | | |
| Tests | Option A | | | | |
| | Option B | | | | |
| | Option C | | | | |

## Deviations

> Components where the recommended option scores ≥ 1 LLM point below the best available alternative.
> Each deviation requires explicit human confirmation at validation.

| Component | Recommended | LLM gap | Justification | Estimated agentic impact |
|-----------|------------|---------|---------------|--------------------------|
| … | | | | |

## Coherence check

| Check | Result | Notes |
|-------|--------|-------|
| No inter-component friction | ✅ / ❌ | |
| Stack consistent with project needs | ✅ / ❌ | |

## Prioritized actions

| Priority | Action | Axis | Cost |
|----------|--------|------|------|
| 1 | | | low / medium / high |
| … | | | |
