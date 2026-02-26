---
name: create-github-pull-request
description: Create GitHub PR with filled template
---

# Create GitHub Pull Request Prompt

Fill a PR template with recent changes in the current branch and create a PR with it.

## Rules

- Use `git` and `gh` commands.
- Read instructions from the template and fill it.
- Use the `git log` commands to get the recent changes IF NOT PROVIDED.
- Do not commit anything, nor create new branches.
- Ask for user validation before creating the PR.

## Ressources

### Contributing

```markdown
@CONTRIBUTING.md
```

### Use this template

```markdown
@.github/pull_request_template.md
```

## Steps

1. Get current branch name, project and repository.
   1. If no branch found, generate one.
2. Get current branch changes.
3. Get template and fill it.
4. Create a beautiful PR title.
5. **Ask user validation.**
6. Use filled template to create a PR.
7. Push it to GitHub.
