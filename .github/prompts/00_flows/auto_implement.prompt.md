---
name: auto_implement
description: Automate all steps of the AI-driven development flow.
---

# Goal

Implement features end-to-end, automatically, using AI-driven development.

Issues to process:

```text
$ARGUMENTS
```

## IMPORTANT RULES

- NEVER ASK QUESTIONS - work autonomously, no human intervention
- EACH step must be 100% successful before proceeding to next
- Work in `worktrees/<branch>/` for isolation
- Use Todo to track progress for each issue

## Steps

### 1. Preparation

1. Parse issue URLs/numbers from arguments
2. Create todo list with all issues to process

### 2. For EACH Issue (Sequential Processing)

**Setup Phase:**

1. Extract issue number and create branch name: `feat/issue-<number>`
2. Fetch issue details: `gh issue view <number> --json body,title,url`
3. Create worktree: `git worktree add worktrees/<branch> -b <branch>`
4. Update todo: mark issue as "in_progress"

**Implementation Phase (all commands with `cwd: worktrees/<branch>`):**

1. Generate technical plan: Use `/plan <issue-url>`
2. Implement changes: Use `/implement`
3. Run tests: Execute test suite if applicable
4. Commit changes: Use `/commit`
5. Code review: Use `/review_code`
6. Functional review: Use `/review_functional`
7. Create PR: Use `/create_github_pull_request`

**Completion Phase:**

1. Record PR URL and status
2. Update todo: mark issue as "completed"
3. Keep worktree (don't delete - needed for PR updates)

### 3. Final Report

1. List all issues processed
2. Show PR URLs created
3. Summary of successes/failures

## Notes

- Worktrees remain in `worktrees/` folder (gitignored)
- Manual cleanup later: `git worktree remove worktrees/<branch>` after PR merge
- If error occurs: log it, mark todo as failed, continue to next issue
