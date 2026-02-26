---
name: extract_flow
description: Extract step-by-step implementation flows from requirements
---

# Extract Flow Prompt

## Goal

Extract generated structured implementation flow from previous conversation that can be re-use to achieve similar features but on other entities.

## Rules

- Must be generic, do not focus on entities, but rather on flow
- Simple tasks: 3-5 phases
- Complex tasks: 5-10 phases
- Very complex: **inform user then we should break into sub-flows**

## Ressources

### Flow template to fill

```markdown
@aidd/prompts/templates/flow.md
```

## Steps

1. Analyze request to detect intent
2. Identify key components (inputs, outputs, dependencies)
3. Ultra think about main phases
4. Add code snippets and file locations
5. Ensure best practices to validate the flow (Web Search if cutting edge tech)
6. Include validation and testing points to ensure flow is perfect
7. **Wait for user validation**
8. Output using flow using template in `docs/flows/<minimal_flow_name>.md`
