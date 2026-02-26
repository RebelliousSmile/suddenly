---
name: implement
description: Implement plan following project rules with validation
argument-hint: The technical plan to implement
---

# Implement Plan Prompt

## Goal

Implement following development plan following project rules with complete validation.

## Rules

- Follow all project rules @docs/rules.md
- Never format code
- Never run dev mode

## Context

### Implementation plan

```text
$ARGUMENTS
```

## Process steps

IMPORTANT: Iterate on those steps until nothing more can be done.

1. Code the whole feature based on the implementation plan.
   1. Start with phase 1.
2. For each phases of the plan, we need to be 100% sure everything is implemented properly.
   1. For each phases, check the sub-tasks
   2. Ensure ALL tasks have been properly integrated for that phase
   3. Re-check the implementation for that phase
   4. Go to the next phase
3. Assert technical stuff:
   1. Typechecking
   2. Tests
   3. Build
4. Iterate on the technical rules
   1. For that given implementation, check the given coding rules
   2. List discrepancies in the produced code
   3. Suggest fixes for the discrepancies
   4. Implement the suggested fixes
   5. Validate the implementation against the rules
   6. Repeat until no more discrepancies
