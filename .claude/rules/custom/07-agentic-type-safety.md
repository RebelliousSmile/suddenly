# Agentic type safety practices

> Source: Agentic Readiness Framework — Principle 2 (Typing)
> Challengeable by `/agentic_architecture` after stack definition.

- Enable strict mode for the project's type checker — without it, the agent infers constraints from narrative context instead of compiler errors
- Type IDs and business values with explicit names, not bare `string` or `int` — prevents the agent from confusing two business identifiers
- No untyped escape hatches (`any`, `mixed`, `object`, `# type: ignore`) without a documented justification comment on the same line
- API contracts should generate client types when the project owns its backend API — hand-written types drift silently
