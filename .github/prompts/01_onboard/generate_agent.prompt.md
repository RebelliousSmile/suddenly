---
name: generate_agent
description: Generates a customized agent based on user-defined parameters.
---

# Goal

Generate a specialized agent template tailored to specific user requirements.

## Context

### Agent template

```markdown
@aidd/prompts/templates/agent.md
```

## Rules

- Input and Output for the agent MUST be ULTRA concise and precise.
- Ask clarifying questions if the user's request is ambiguous or lacks detail.

## Instruction steps

1. Ask following questions to the user until you gather all necessary information in agent's template.
   1. Discuss with the user until you have a clear understanding of the agent's purpose, tools, and instructions.
   2. Use the gathered information to fill in the agent template.
2. Review the generated agent to ensure it is straightforward with 0 ambiguity.
   1. Affect a note between 1 and 10 to the generated agent based on its relevance and completeness.
3. **Wait for user confirmation before finalizing the agent.**
4. Provide the completed agent template as the final output into `docs/agents/<generated-agent-name>.md`.
