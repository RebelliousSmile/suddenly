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

`users`, `games`, `characters`, `activitypub`, `api`

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

## Concurrent Claude Code sessions

- Two sessions can work the same repo/branch at once — a plain `runserver` process is not proof of activity; a new commit or a file vanishing from `git status` between two consecutive checks is
- `endtask`: if the branch to merge shows uncommitted changes appearing between checks (or unexpected new commits), stop before merge/push/branch-delete/changelog/tag/issue-close — commit + push + archive-plan only, leave the rest for a manual follow-up once the other session is confirmed done
- To finish `endtask` without disturbing an active session's shared working directory, do the merge/tag/push in an isolated `git worktree` (not a checkout in the primary working directory) — `git branch -D` on the source branch will correctly fail if it is still checked out elsewhere, which is the expected safety net, not a bug

## Pull Requests

- One PR = one coherent feature or fix
- PR is understandable without oral context
- Any PR modifying ActivityPub API documents Mastodon compatibility impact
- Static analysis clean and tests pass before requesting review
