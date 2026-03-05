# Agentic tooling practices

> Source: Agentic Readiness Framework — Principle 3 (Tooling)
> Challengeable by `/agentic_architecture` after stack definition.

- A single command must run typecheck + lint + tests + coverage — every separate undocumented command is a decision delegated back to the agent
- Lint and format enforced in pre-commit hook AND in CI — formatting left to discretion introduces non-determinism
- CI must block merge on any criterion failure — a CI that does not block is more dangerous than no CI (false sense of security)
- Linter in CI runs in check mode (not auto-fix) — a CI that silently corrects hides problems instead of reporting them to the agent
