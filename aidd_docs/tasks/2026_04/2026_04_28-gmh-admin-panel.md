# Instruction: GMH Admin Panel

## Feature

- **Summary**: Add a dedicated instance administration panel at `/gmh/` with an explicit `is_admin` role, a singleton `InstanceSettings` model (name, description, language), and propagation of these settings to the active Django locale (for new users), the context processor (SITE_NAME/SITE_DESCRIPTION), and NodeInfo federation metadata.
- **Stack**: `Django 4.x`, `Python 3.12`, `HTMX`, `Alpine.js`, `UnoCSS`
- **Branch name**: `feat/gmh-admin-panel`
- **Parent Plan**: `none`
- **Sequence**: `standalone`
- Confidence: 9/10
- Time to implement: 2–3h

## Existing files

- @suddenly/core/admin_views.py
- @suddenly/core/admin_urls.py
- @suddenly/core/context_processors.py
- @suddenly/core/middleware.py
- @suddenly/core/models.py
- @suddenly/users/models.py
- @suddenly/urls.py
- @suddenly/activitypub/wellknown_urls.py
- @suddenly/users/adapters.py
- @config/settings/base.py
- @templates/base.html

### New files to create

- `suddenly/core/decorators.py` — `@admin_required` decorator
- `templates/gmh/base.html` — admin layout with sidebar nav
- `templates/gmh/dashboard.html`
- `templates/gmh/instance_settings.html`
- `suddenly/core/management/commands/set_admin.py` — CLI to promote a user to admin

## User Journey

```mermaid
flowchart TD
  A[manage.py set_admin username] --> B[User logs in]
  B --> C[Admin link visible in nav]
  C --> D[/gmh/ dashboard]
  D --> E[/gmh/settings/ — form]
  E --> F[Submit: name + description + language]
  F --> G[InstanceSettings saved in DB]
  G --> H[Context processor → SITE_NAME updated]
  G --> I[InstanceLanguageMiddleware → locale activée pour utilisateurs sans préférence]
  G --> J[NodeInfo languages field updated]
```

## Implementation phases

### Phase 1: Data layer

> Add `is_admin` to User, create `InstanceSettings` singleton, migrations.

1. Add `is_admin = models.BooleanField(default=False)` to `User` model in `suddenly/users/models.py`
2. Add data migration: set `is_admin=True` for all users where `is_staff=True` (preserves existing admins)
3. Create `InstanceSettings` model in `suddenly/core/models.py`:
   - `name: CharField(max_length=100, blank=False)` — instance name (required)
   - `description: TextField(blank=True)` — instance description
   - `language: CharField(max_length=10, choices=settings.LANGUAGES, default="fr")` — default locale
   - `registrations_open: BooleanField(default=True)` — whether new signups are allowed
   - Singleton enforced via `save()` override (pk always = 1)
   - Class method `get()` returning the singleton (creates with Django settings defaults if absent), result cached in Django cache (key `instance_settings`, TTL 300s) — invalidated on save; wraps DB access in `try/except OperationalError` and returns a default object if DB is unavailable (boot-safe)
4. Generate and apply migrations
5. Create management command `set_admin <username>`: sets `is_admin=True`, prints confirmation

### Phase 2: Admin panel at `/gmh/`

> Rename URL, create access decorator, migrate existing views, add admin base template.

1. Create `suddenly/core/decorators.py` with `@admin_required`: checks `request.user.is_authenticated and request.user.is_admin`, redirects to login otherwise
2. Replace `@staff_member_required` with `@admin_required` in `admin_views.py`
3. In `suddenly/urls.py`: rename mount `admin-panel/` → `gmh/`, keep `path("admin-panel/", RedirectView(..., url="/gmh/"))` for backward compat
4. Create `templates/gmh/base.html` extending `base.html` — left sidebar with: Dashboard, Instance settings
5. Update existing admin templates to extend `gmh/base.html`

### Phase 3: Instance settings view

> Form to edit InstanceSettings (name, description, language).

1. Add `instance_settings` view (GET/POST) in `admin_views.py` — reads/writes `InstanceSettings.get()`, invalidates cache on save
2. Add URL `settings/` → `instance_settings` in `admin_urls.py`
3. Create `templates/gmh/instance_settings.html` — form with name, description, language `<select>` built from `settings.LANGUAGES`, and a switch for `registrations_open`

### Phase 4: Propagation

> Active locale, context processor, and NodeInfo all reflect InstanceSettings.

1. In `suddenly/core/middleware.py`, add `InstanceLanguageMiddleware`:
   - Unconditionally calls `translation.activate(InstanceSettings.get().language)` — sets the instance default
   - Uses cached `InstanceSettings.get()` — no extra DB hit
2. Register `InstanceLanguageMiddleware` in `settings/base.py` MIDDLEWARE list, **before `UserLanguageMiddleware`** so that `UserLanguageMiddleware` can override the instance default with the user's personal preference when set
3. Update `context_processors.py`: use `InstanceSettings.get()` to populate `SITE_NAME` and `SITE_DESCRIPTION` (keep `try/except` fallback to Django settings in case DB is unreachable at boot)
4. Update nodeinfo view in `activitypub/`: populate `languages: [InstanceSettings.get().language]` and `openRegistrations: InstanceSettings.get().registrations_open` in the NodeInfo 2.0 response
5. In `suddenly/users/adapters.py` (`SuddenlyAccountAdapter`):
   - Override `is_open_for_signup(request)` → return `InstanceSettings.get().registrations_open`
   - Update `send_mail` to use `InstanceSettings.get().language` instead of `settings.LANGUAGE_CODE`
6. Add admin nav link in `templates/base.html` user dropdown: shown only when `request.user.is_authenticated and request.user.is_admin`

## Validation flow

1. `python manage.py set_admin <username>` → success message
2. Log in → admin link visible in user dropdown
3. `/gmh/` → dashboard with stats
4. `/gmh/settings/` → form with defaults from Django settings
5. Set name = "Mon Instance", language = "en" → save
6. Any page `<title>` → "Mon Instance"
7. Anonymous request → interface in English
8. `curl /.well-known/nodeinfo/2.0` → `languages: ["en"]`, `openRegistrations: true`
9. Set `registrations_open = False` → signup page blocked (redirect or 403)
10. `/admin-panel/` → 301 redirect to `/gmh/`
11. Non-admin accessing `/gmh/` → redirect to login
12. `make check` → all green
