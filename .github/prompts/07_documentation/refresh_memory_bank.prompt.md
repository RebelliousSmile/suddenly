---
name: refresh_memory_bank
description: Refresh (aka create or update) the memory bank files to reflect the current state of the codebase
argument-hint: <module> (optional) - default is project root
---

# Refresh Memory Bank

Means to create or update the documentation files that make up the memory bank of the project.

Only change existing files if there is REAL CHANGES in the codebase, do not change files just to reformat or reword things.

If $ARGUMENTS is provided, it will be the module/folder to analyze, otherwise use project root.

## Resources

Every file has its own template to follow.

### Common

Used for each module! (Backend, Frontend, etc...)

- aidd/prompts/templates/memory-bank/common/ARCHITECTURE.md
- aidd/prompts/templates/memory-bank/common/CODING_ASSERTIONS.md
- aidd/prompts/templates/memory-bank/common/TESTING.md

### Backend Specific

- aidd/prompts/templates/memory-bank/backend/API_DOCS.md
- aidd/prompts/templates/memory-bank/backend/DATABASE.md

### Frontend Specific

- aidd/prompts/templates/memory-bank/frontend/BACKEND_COMMUNICATION.md
- aidd/prompts/templates/memory-bank/frontend/DESIGN.md
- aidd/prompts/templates/memory-bank/frontend/FORMS.md

### Documentation Root

- aidd/prompts/templates/memory-bank/PROJECT_BRIEF.md
- aidd/prompts/templates/memory-bank/DEPLOYMENT.md
- aidd/prompts/templates/memory-bank/STACK.md
- aidd/prompts/templates/memory-bank/CODEBASE_STRUCTURE.md

## Steps

1. Check if memory bank already exist in `docs/memory-bank` folder:
   1. If exists, update it with newer information.
   2. If not exist, create them from scratch.
2. Determine modules to analyze:
   1. If $ARGUMENTS is provided, it will be the module/folder to analyze.
   2. If not provided, use project root.
3. Provide the modules list to USER.
4. **Wait for user approval** before proceeding.
5. For each module, identify which files to create/update:
   - Common: `docs/memory-bank/<module>/<file>.md`
   - Backend specific: `docs/memory-bank/backend/<file>.md`
   - Frontend specific: `docs/memory-bank/frontend/<file>.md`
   - Documentation root: `docs/memory-bank/<file>.md`
6. Spawn a new task agent for each template file to analyze the codebase and fill its own template (in parallel) based on rules below.
7. Output the generated files in proper dir.
8. Synchronize AGENTS.md with memory bank executing: `sh aidd/assets/scripts/aidd-generate-docs.sh --memory-bank`

## Rules

- "?" means optional, do not add section if not applicable
- Templates give optional sections, feel free to add or remove sections as needed
- ZERO DUPLICATION: Focus only on the sections in template to avoid duplication across files
- No minor versions in libs (e.g. `Next.js 15.3.4` → `Next.js 15` )
- Templates follow clear separation of concerns
- For config files (e.g. `package.json`, API schema etc...), please include relative based path using "@" (do not surrounded path with backticks)
- SUPER SHORT explicit and concise bullet points
- Mention code using backticks
