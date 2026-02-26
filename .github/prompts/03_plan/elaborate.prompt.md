---
name: elaborate
description: Create and refine feature requests through interactive dialogue.
---

# Goal

Create and refine feature requests through interactive dialogue with the user, then delegate plan generation to the plan command.

## Steps

### Step 1: Gather and Refine Feature Request

> Do not analyze codebase yet

Make this iteration until no more questions are raised:

1. With no technical aspect, detail the feature request in bullet points understanding user intentions and requirements
2. List inconsistencies, ambiguities and answers them
3. Review your work and list check for edge cases
4. Replay steps 2-3 until no more questions
5. Display final feature requirements to user

- **WAIT FOR USER APPROVAL** before proceeding

### Step 2: Delegate to Plan Command

After user approves the feature request:

1. Format the approved requirements as structured text
2. Run and execute `aidd/prompts/ide/03_plan/plan.md` with the structured requirements as ARGUMENT
