# Master Plan: i18n + Instance Versioning

## Feature

- **Summary**: Add full Django i18n support with **English as source language** and French as primary translation, per-instance default (env-driven), per-user override via NEW `interface_language` field, force instance language for transactional emails, fix instance version exposure via context processor + NodeInfo + /about, ship contributor docs.
- **Stack**: `Django 5.0.14`, `django-allauth`, `importlib.metadata`, `pytest-django`, `gettext`
- **Branch strategy**: 3 separate branches (`feat/i18n-infra`, `feat/i18n-templates`, `feat/i18n-user-pref`), each PR shippable independently in order
- **Parent Plan**: `none`
- **Sequence**: `master`
- **Confidence**: 9/10
- **Time to implement**: ~3 days (English rewrite of templates is the new bottleneck)

## Child Plans

| Part | File | Goal | Status |
|------|------|-------|--------|
| 1 | [Part 1](2026_04_28-i18n-versioning-part-1.md) | Infrastructure i18n + version fix + `fr-fr→fr` audit | pending |
| 2 | [Part 2](2026_04_28-i18n-versioning-part-2.md) | English rewrite + balisage 66 templates + Python strings + catalogues + tests | pending |
| 3 | [Part 3](2026_04_28-i18n-versioning-part-3.md) | `interface_language` field + middleware (avec deactivate) + emails forcés + doc contributeurs | pending |

## User Journey

```mermaid
flowchart TD
  A[Admin sets LANGUAGE_CODE env per instance] --> B[Visitor lands]
  B --> C{Authenticated?}
  C -- No --> D[LocaleMiddleware: instance default + Accept-Language]
  C -- Yes --> E[UserLanguageMiddleware reads user.interface_language]
  D --> F[Interface rendered]
  E --> F
  F --> G[User edits profile → picks UI language]
  G --> H[Saved to interface_language NEW field]
  G --> F
  I[set_language built-in for anonymous nav switcher] --> F
  J[Email triggered] --> K[Adapter wraps with translation.override settings.LANGUAGE_CODE]
  K --> L[Email always in INSTANCE language]
  M[Anyone or Fediverse crawler] --> N[/about + NodeInfo show real version + actually-translated languages]
```

## Architectural Decisions (FINAL)

- **Source language = English** (msgid in English; `msgstr` in French for fr.po)
  - Rationale: international project, standard convention, contributors expect English keys
  - Cost: rewrite all template strings to English before wrapping in `{% trans %}`
- **NEW field `interface_language` on User model** — `content_language` is used for content filtering (admin, form, template confirmed) and must NOT be repurposed
  - Field type: `CharField(max_length=10, blank=True, default="")` — empty means "use instance default"
- **Instance default via env**: `LANGUAGE_CODE = os.environ.get("LANGUAGE_CODE", "fr")` (no `django-environ` available)
- **Normalize `LANGUAGE_CODE` `fr-fr` → `fr`** — only one occurrence in `base.py`, no risk
- **No URL prefixes** (`i18n_patterns` not used)
- **Emails forced to `settings.LANGUAGE_CODE`** via custom `AccountAdapter`
- **`.po` committed, `.mo` gitignored**, `compilemessages` at deploy
- **CI guardrail**: `python manage.py makemessages` + `git diff --exit-code locale/` (Django 5.0 has no `--check` flag — verified)
- **NodeInfo `metadata.languages`** computed from actually-compiled `.mo` files, not just `LANGUAGES` setting

## Confidence Assessment

- ✅ All 5 deal breakers from first challenge addressed
- ✅ All deal breakers from second challenge addressed:
  - Source language decided (English)
  - Middleware deactivate planned
  - `os.environ.get()` confirmed (no env helper)
  - `--check` flag rejected, alternative chosen
  - `fr-fr` audit trivial (single occurrence)
- ✅ `content_language` actual usage verified — new field justified
- ❌ English rewrite of 66 templates inflates Part 2 timeline (8h → ~1.5 days)
- ❌ `gettext` system dependency — must be in DEPLOYMENT.md
