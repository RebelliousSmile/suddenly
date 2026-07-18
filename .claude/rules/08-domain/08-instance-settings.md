---
paths:
  - "suddenly/core/**"
  - "suddenly/**/context_processors.py"
  - "suddenly/**/middleware.py"
  - "config/settings/**"
---

# InstanceSettings singleton

- Read instance config via `InstanceSettings.get()` — never `InstanceSettings.objects.first()` or `.get(pk=1)`
- The model is a forced singleton (`pk=1`); `get()` creates the row if absent
- Wrap accesses in migrations or at startup with `try/except (OperationalError, ProgrammingError)` — table may not exist yet
- `SITE_NAME` and `SITE_DESCRIPTION` in `settings.py` are optional fallbacks only — runtime values come from `InstanceSettings`
- Propagate via `core.context_processors`, `InstanceLanguageMiddleware`, and NodeInfo metadata builders
  **Why:** instance config must be editable by a non-technical admin without redeploy; `objects.first()` returns `None` on a fresh DB and breaks the singleton invariant.
