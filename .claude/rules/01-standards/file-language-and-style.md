---
description: 'Project file language and style depend on audience. LLM-consumed files in English and concise. Human-consumed files in French and readable. Apply when creating or editing any project markdown file.'
---

# Project file language and style

## Audience-driven choice

- LLM-consumed file → English
- Human-consumed file → French
- One file = one audience

## LLM-consumed paths

- `.claude/**` (skills, rules, agents, commands)
- `aidd_docs/templates/**`
- `aidd_docs/memory/**` (auto-loaded into context)

## Human-consumed paths

- `README.md`, `CHANGELOG.md`
- `aidd_docs/tasks/**` (plans, reviews, journeys)
- `aidd_docs/harvests/**` (reports)
- `aidd_docs/audits/**` (audits)
- ADRs, postmortems, design docs

## Style — LLM-consumed

- Bullets only, no prose
- 3-15 words per bullet
- Named symbols, not paraphrase
- No emoji, no filler
- Code blocks for commands or patterns

## Style — human-consumed

- Readable, fluent prose
- Sections with H2/H3
- Concise but explanatory
- Examples when they aid understanding
- Tables for comparisons

## Out of scope

- Code files (.ts, .vue, .js, .py, ...) — follow code-style rules
- Chat responses — follow `Language` directive
- Already-covered paths inherit existing rules without duplication
