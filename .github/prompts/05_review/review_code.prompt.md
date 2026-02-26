---
name: review_code
description: Ensure code quality and rules compliance
---

# Code Quality Review Prompt

## Goal

Review code changes against project rules and identify quality violations.

## Rules

- Git diff analysis
- Deep detail review
- Check all lines of diff
- Apply project rules strictly
- Focus on issues only
- Use review template format

### Project rules

@docs/rules.md

## Process steps

1. Based on the project rules and global clean code principles, perform a deep code review of the changes.
2. If no specific arguments, use `git diff main` to have changes to review
3. Format using template @aidd/prompts/templates/code_review.md
4. Output in `docs/tasks/yyyy_mm_dd_<task_name>.review.md`
