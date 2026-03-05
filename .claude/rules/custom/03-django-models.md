---
paths:
  - "suddenly/**/models.py"
---

# Django models conventions

- All models inherit from `core.models.BaseModel` (UUID PK, timestamps)
- Use `select_related` / `prefetch_related` in all querysets that cross relations
- No business logic in models — delegate to services
- ForeignKey fields must specify `on_delete` explicitly
- Use `Meta.constraints` and `Meta.indexes` over ad-hoc DB migrations
