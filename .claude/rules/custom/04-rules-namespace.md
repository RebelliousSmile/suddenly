# Rules namespace convention

- `.claude/rules/custom/` is the project namespace — all project-specific rules go here
- Directories outside `custom/` (`01-standards/`, `02-programming-languages/`, `03-frameworks-and-libraries/`, `04-tooling/`, `05-testing/`, `06-design-patterns/`, `07-quality/`, `08-domain/`, `09-other/`) belong to the AIDD framework core and must not be modified by project commands or agents
- When generating rules via `/agentic_architecture` or `/generate_rules`, always target `custom/` with the category prefix in the filename (e.g. `custom/03-django-models.md`, `custom/08-activitypub.md`)
- This separation allows updating the AIDD framework without losing project customizations
