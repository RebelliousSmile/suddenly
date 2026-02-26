---
name: assert_frontend
description: Make sure a frontend feature works as intended.
argument-hint: The frontend behavior you need to assert and validate.
---

# Goal

Assert that this frontend feature works as intended:

```text
$ARGUMENTS
```

## Rules

- Use MCP when navigating URL
- Use task template to track your progress
- Suppose all servers are already started

## Ressources

### Tracking issue template

```markdown
@aidd/prompts/templates/task.md
```

## Steps

Iterate over those steps until the feature work as intended.

1. Summarize user need, if something fundamental is missing stop
2. List action paths (e.g. user clicks button -> calls function in file1 -> updates state in file2...).
3. Reproduce the issue
4. List 3 best potential causes with small description + confidence level.
5. Assert that the first one is the root cause by checking the logs and reproducing the issue.
   1. Are you sure +90%? If so continue
   2. If not retry until +90% sure
6. Fix the issue.
7. Try to reproduce the issue.
   1. If not, issue if fixed, inform user.
   2. If yes, replay every steps
8. Inform user how you did resolve it.
   1. How could we find this error earlier?
   2. What need to be done in order for that error not to happen?
