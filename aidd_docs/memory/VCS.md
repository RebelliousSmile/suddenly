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
- Imperative mood: "add" not "added"
- Lowercase, no period, max 72 chars
- One commit = one logical intent

### Types

| Type | Usage |
|------|-------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code change (no feat/fix) |
| `docs` | Documentation only |
| `test` | Add/update tests |
| `chore` | Build, config, deps |
| `style` | Formatting (no logic change) |
| `ci` | CI/CD configuration |
| `revert` | Revert previous commit |
| `perf` | Performance improvement |

### Scopes

`users`, `games`, `characters`, `quotes`, `activitypub`, `api`

### Rules

- Tests pass before every commit
- No `WIP`, `fix`, `update` without description on `main`
- No author name, copyright, `Co-authored-by` in commit messages
- Max 5 bullet points in body — synthesize if more

### Examples

```
feat(characters): add fork link request workflow
fix(activitypub): handle missing inbox URL
refactor(games): extract service layer
test(characters): add contract tests for status transitions
```

## Pull Requests

- One PR = one coherent feature or fix
- PR is understandable without oral context
- Any PR modifying ActivityPub API documents Mastodon compatibility impact
- Static analysis clean and tests pass before requesting review
