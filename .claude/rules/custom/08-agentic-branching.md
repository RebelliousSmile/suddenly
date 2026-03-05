# Agentic branching practices

> Source: Agentic Readiness Framework — Branching and conflict management
> Challengeable by `/agentic_architecture` after stack definition.

- Rebase on main before starting any work session — divergence increases conflict complexity and agent error risk
- One commit = one intent with an explicit message — clear messages are context the agent reads to understand why a change was made
- Never resolve a merge conflict on core business logic files without human validation — report the conflict and stop
- Branches should live < 3 days in multi-agent context — daily rebase as default rule
- Before parallel agent work, identify overlapping files and assign scopes to minimize intersections
