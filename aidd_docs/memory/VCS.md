# Versioning Control System (VCS) Guidelines

- Main Branch: `main`
- Platform: GitHub
- CLI or MCP: `gh` ou `mcp__github__*`
- Ticketing Tool: N/A

## Branch Naming Convention

- Pattern: `type/short-description`
- Lowercase, hyphen-separated
- Examples: `feat/character-adoption`, `fix/activitypub-inbox`, `refactor/user-models`

## Commit Convention

- Pattern: `type(scope): description`
- Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`
- Scopes: `users`, `games`, `characters`, `quotes`, `activitypub`, `api`
- Example: `feat(characters): add fork link request workflow`
