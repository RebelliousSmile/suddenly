---
paths:
  - "suddenly/**/views.py"
---

# Django views conventions

- Views are thin — delegate logic to services
- HTMX partials return fragments, not full pages
- Use `LoginRequiredMixin` or `@login_required` for protected views
- No ORM queries beyond simple lookups — complex queries go in services
- Return proper HTTP status codes (201 for create, 204 for delete)
