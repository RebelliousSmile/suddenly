---
name: assert
description: Assert that a feature must work as intended.
argument-hint: Feature or behavior to assert and validate.
---

# Goal

Assert that this feature works as intended:

```text
$ARGUMENTS
```

## Rules

- Use task template to track your progress

## Ressources

### Coding assertions to strictly follow

```markdown
@docs/CODING_ASSERTIONS.md
```

### Tracking issue template

```markdown
@aidd/prompts/templates/task.md
```

## Steps

Iterate over those steps until the feature work as intended.

1. List assertions to validate the feature.
2. For each assertion, fix any issues preventing it from passing.
3. After fixing, re-run the assertions to confirm they all pass.
4. Once all assertions pass, re-run all the checks again to ensure every assertions are passing.
