# Agentic test practices

> Source: Agentic Readiness Framework — Principle 1 (Tests)
> Challengeable by `/agentic_architecture` after stack definition.

- Enforce coverage at 100% on new and modified files in CI — below that, the agent makes subjective choices about what "deserves" testing
- Unit test suite must complete in < 60s — a slow suite discourages the agent from running tests after every change
- Unit tests must not depend on database, network, or external APIs — mock or cache all external calls
- No test file without meaningful assertions — execution is not correctness
- Coverage threshold must be enforced (not just measured) — an unenforced metric gives the agent no signal
