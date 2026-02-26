---
name: commit
description: Create git commit with proper message format
---

# Commit Prompt

## Goal

Generate git commit with standardized message following project conventions.

## Rules

- Keep commits atomic and focused
- Conventional commits
- Clear change description
- Follow previous commit message format
- Include change type prefix
- Concise but descriptive
- Reference issues if applicable
- Write in imperative mood ("Add feature" not "Added feature")
- Explain why, not just what

## Context

### Commit rules

```markdown
@docs/COMMIT.md
```

### Previous commits

```text
!`git log -5 --pretty=%B`
```

## Process steps

1. If branch does not exist, propose a name based on changes + **WAIT FOR USER APPROVAL**
2. Check staged changes
3. Determine change type (feat, fix, docs, etc)
4. Suggests splitting commits for different concerns:
   1. Make a list of functional changes with clear commit messages
5. **WAIT FOR USER APPROVAL**
6. Execute git add patch for dedicated part of the feature
7. Run git commit with generated messages
8. If pre-commit errors, fix and retry to commit:
   1. loop here until you can commit
9. Verify commits success
10. List them to user
