---
name: agentic_architecture
description: Generate project architecture with an agentic readiness audit — scores the project against the Agentic Readiness Framework before designing agents, skills, and commands.
argument-hint: Project description and domain requirements
model: opus
---

# Agentic Architecture

## Context

### Memory bank

```markdown
@aidd_docs/memory/
```

### Agentic Readiness Framework

```markdown
@aidd_docs/templates/custom/agentic_readiness_framework.md
```

### Generate architecture instructions

```markdown
@.claude/commands/aidd/01/generate_architecture.md
```

### Audit score template

```markdown
@aidd_docs/templates/custom/audit_score.md
```

### Architecture summary template

```markdown
@aidd_docs/templates/custom/architecture_summary.md
```

### Arguments

```text
$ARGUMENTS
```

## Goal

Run an agentic readiness audit, then generate the project architecture.

## Steps

1. Run the agentic readiness audit and write the filled result to `aidd_docs/tasks/{YYYY_MM}/audit_result.md` following `audit_score.md`. The audit has four sub-steps:
   - **Needs analysis**: read CLAUDE.md, existing code, and docs to extract functional and technical constraints. If the project has no existing code (greenfield), ask the human about stack preferences before continuing and document the answers in the "Project needs analysis" section.
   - **Axis scoring**: evaluate each criterion — tests (framework, coverage enforcement, speed, mocking), type safety (strict mode, checker in CI, primitive IDs, inferred types), tooling (unified check command, lint tool, pre-commit hook, CI), agent context (CLAUDE.md, boundaries, rules files).
   - **Stack alternatives**: for each component (language, framework, DB, ORM, tooling, CI, tests), propose 3 alternatives using current LLM knowledge or web search. Infer human supervision score from project context (3 = in codebase, 2 = in CLAUDE.md only, 1 = absent). Compute Combined score (LLM × 0.6 + Sup × 0.4). Flag any deviation where the recommended option scores ≥ 1 LLM point below the best available alternative.
   - **Coherence check**: verify the retained stack has no inter-component friction and is consistent with the needs identified in the first sub-step.
2. Present the audit score to the user — **wait for explicit user approval before continuing**
3. Delegate to `alexia` agent with the following prompt:
   - Current project state (from memory bank)
   - Audit score from `aidd_docs/tasks/{YYYY_MM}/audit_result.md` and prioritized ❌ signals to address as architecture gaps
   - Full generate_architecture instructions (loaded above) to follow
   - Constraint: validate the complete architecture plan with the user BEFORE creating any file
   - Constraint: write the final report following `architecture_summary.md` to `aidd_docs/tasks/{YYYY_MM}/architecture_result.md`
4. Only if `aidd_docs/tasks/{YYYY_MM}/architecture_result.md` is complete and follows `architecture_summary.md` — update memory bank (scope: `architecture.md` and `codebase_map.md`) using it as input. If the file is missing or incomplete, report the gap to the user and stop:

```markdown
@.claude/commands/aidd/07/learn.md
```
