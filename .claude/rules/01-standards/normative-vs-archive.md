---
description: 'Normative content (must / never / always) must live in auto-loaded paths. Historical records belong in archives. Apply when reviewing, organizing or migrating project documentation.'
---

# Normative load — auto-loading required

## Principle

- Normative weight is capped by load probability
- Normative document → auto-loaded context
- Historical document → archive read on demand
- One document = one role only

## Identifying normative content

- Words `must / never / always / required / forbidden`
- Names a file, function, flag or constant binding the future
- Describes a convention to follow

## Identifying historical content

- Date + rationale of a past decision
- Alternatives evaluated and rejected
- Measured baseline, postmortem
- Completed plan

## Violation symptoms

- A `decisions/`, `adr/`, `internal/`, `archive/` directory read as if it were rules
- Convention repeated in conversation when it is already written somewhere
- Archive denser than the auto-loaded context
- Document mixing rule and journal without separation

## Action

- Extract normative content to the auto-loaded context
- Keep the archive only if it carries rationale or alternatives
- Otherwise delete after migration
- Trace the migration

## Why

- The agent does not consult opt-in paths during implementation
- A decision not loaded weighs zero on code being written now
- The gap between normative weight and load probability is silent
