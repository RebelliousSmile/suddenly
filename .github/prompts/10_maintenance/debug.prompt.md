---
name: debug
description: Debug issue to find root cause.
---

# Goal

Debug an issue in the codebase using `sequential-thinking` to eliminate not-valid assumptions.

## Rules

- For selected causes, use MCP if necessary.
- Draw a quick fix plan.

## Steps

You will create a list of potential causes for the issue, for each of them, keep trace in a todo list of the actions you took to validate or invalidate the cause.

1. Summarize the issue with you own words.
2. List action paths (e.g. user clicks button -> calls function in file1 -> updates state in file2...).
3. Find relevant files to find bug in codebase based on issue description.
4. List 3 best potential causes with:
   1. Analysis
   2. Evidences
   3. Confidence level (1 out of 10)
5. **Wait for user validation.**
