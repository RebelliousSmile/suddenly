---
paths:
  - "suddenly/users/**"
  - "suddenly/core/**"
  - "suddenly/**/decorators.py"
  - "suddenly/**/views.py"
  - "suddenly/**/front_views.py"
---

# Admin roles — `is_admin` vs `is_staff`

- `is_staff` is reserved for the Django admin UI — never check it for instance moderation
- Instance admin gating uses `User.is_admin` (BooleanField, default False)
- Always protect instance-admin views with `@admin_required` — never `@staff_member_required`
- `@admin_required` checks `is_authenticated AND is_admin`
- Promote a user with `python manage.py set_admin <username>` — no UI shortcut
  **Why:** `is_staff` grants Django admin access (a database-level surface); instance admins need only moderation/settings, so the two roles must stay separate to limit blast radius.
