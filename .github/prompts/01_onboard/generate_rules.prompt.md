---
name: generate_rules
description: Generate or modify coding rules for the project's rule-based architecture system
argument-hint: module (optional)
---

# Generate Rules

## Goal

Generate or modify coding rules based on the current project.

## Outcome

Create structured .mdc rule files with proper front-matter and content in appropriate directories

## Ressources

### Template

```markdown
@aidd/prompts/templates/rule.md
```

## Constraints to respect

- But be concise, less is more

### When writing Rules

- When mentioned existing specific code, please mention full file path prefixed by "@" (no backticks, no need to write folder mentions)
- Format globs without "@"
- Backticks for code ref
- Bullet points only
- Remove non-essential, no fluff
- 1 ultra short (3–7 words) rule per bullet point

#### When writing Rule examples (optional?)

- Use tiny generic example peer group IF NEEDED
- Good code only

### File name format

```text
#-rule-name[@version][-specificity].mdc
```

- `#` : Number based on dir structure
- `-rule-name` : Slugified short rule name
- `@version` : (optional)
- `-specificity` : Sub-part (optional)
- `.mdc` : Extension

### Directory structure

Output rules in `docs/rules/<module>/` where `<module>` is the module name provided as argument to the command.

Module is : """$ARGUMENTS""" (if empty, use root `docs/rules/`)

Each rule must be in its own folder.

| #    | Folder         | Content                        | Examples                              |
| ---- | -------------- | ------------------------------ | ------------------------------------- |
| `00` | `architecture` | System-level patterns          | Clean, Onion, API design              |
| `01` | `standards`    | Code style, naming             | camelCase, imports                    |
| `02` | `languages`    | Language rules                 | TypeScript strict                     |
| `03` | `libs-frameworks`   | Framework usage                | React hooks, Vite, Zod...                  |
| `04` | `tooling`      | Dev tools                      | ESLint, Docker                        |
| `05` | `workflows`    | Processes                      | Git flow, PR, CI/CD                   |
| `06` | `patterns`     | Code patterns                  | Repository, Factory                   |
| `07` | `quality`      | Testing, security, perf        | Test structure, headers               |
| `08` | `domain`       | HOW implémenter business logic | Validation patterns, entities, errors |
| `09` | `other`        | Misc                           | Edge cases                            |

Example:

```text
docs/rules/<module>/03-frameworks-and-libraries/
├── 3-react.mdc
├── 3-react@18.mdc
├── 3-react@19.mdc
├── 3-react@19-hooks.mdc
└── 3-react@19.1-hooks.mdc
```

## Steps

Please follow the following steps (make sure User is validation before doing anything):

0. Remind the project's context, including tech stack, versions, architecture, and existing rules.
1. Ask user which rules to generate?
2. Check if rule exists
   1. Exists → Update existing rule
   2. New → Create from scratch
3. Design rule structure
   1. Define groups and sub-groups
   2. Display proposed architecture
   3. **Get user approval**
4. Generate the rule
   1. Analyze codebase for examples
   2. For each group/sub-group, generate content
   3. **Get user approval**
5. Save to `docs/rules/<module?>/xxx.mdc`
