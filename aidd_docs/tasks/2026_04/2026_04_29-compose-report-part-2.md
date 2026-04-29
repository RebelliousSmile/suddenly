# Instruction: Compose Report — page and view

## Feature

- **Summary**: Create a dedicated `/games/compose/` page where an authenticated user can write a report linked to a character (and its game). Mobile-friendly, no modal.
- **Stack**: `Django 4+`, `HTMX`, `Alpine.js`, `UnoCSS`, `pytest-django`
- **Branch name**: `feat/compose-report`
- **Parent Plan**: `./2026_04_29-compose-report-master.md`
- **Sequence**: `2 of 3`
- Confidence: 9/10
- Time to implement: 60min

## Existing files

- @suddenly/games/front_views.py
- @suddenly/games/front_urls.py
- @templates/games/report_create.html

### New file to create

- `templates/games/report_compose.html`

## User Journey

```
GET /games/compose/?character=<slug>
        ↓
Compose page loads
  - Character selector pre-filled (filtered: origin_game.owner = me, not remote)
  - Language selector (default: InstanceSettings.get().language)
  - Content warning input (optional text)
  - Visibility radios (public / unlisted / followers)
  - Content textarea (Markdown + @mention support)
        ↓
POST /games/compose/
        ↓
Validation: character exists, game owned by user
        ↓
Report.create(game=character.origin_game, language=..., ...)
ReportCast.create(report=report, character=character, role=CastRole.MAIN)
        ↓
action=publish → set status=PUBLISHED, published_at=now()
action=draft   → leave status=DRAFT
        ↓
redirect → games:report_detail
```

## Implementation phases

### Phase 1 — URL

1. Add to `suddenly/games/front_urls.py`:
   - `path("compose/", front_views.report_compose, name="compose")`

### Phase 2 — View

1. Add imports to `suddenly/games/front_views.py`: `CastRole`, `ReportCast` (from `.models`), `InstanceSettings` (from `suddenly.core.models`)
2. Add `report_compose(request)` to `suddenly/games/front_views.py`:
   - `@login_required`
   - `GET`: resolve `?character=<slug>`, build character queryset filtered on `origin_game__owner=request.user, origin_game__remote=False`, pass to context with `InstanceSettings.get().language` as default language
   - `POST`: validate character + game ownership, create `Report` + `ReportCast(role=CastRole.MAIN)`, handle publish/draft action, redirect to detail
   - Error if character has no `origin_game` → render form with error message
   - Empty queryset (no eligible characters) → render form with empty-state message and link to character creation
   - Use `htmx_render()` pattern consistent with other views

### Phase 3 — Template

1. Create `templates/games/report_compose.html` extending `base.html`:
   - Breadcrumb: `Reports › New`
   - Character `<select>`: view passes `selected_character_slug` (from `?character=`) to context; template uses `{% if char.slug == selected_character_slug %}selected{% endif %}` (server-side, no JS)
   - Language `<select>` with `settings.LANGUAGES` choices, default from context
   - Content warning `<input type="text">` (optional)
   - Visibility radios — reuse pattern from `report_create.html`
   - Content `<textarea>` with `@mention` support (`mentionInput` is a global Alpine.data component defined in `frontend/src/main.js` — usable as `x-data="mentionInput('')"`)
   - Empty state if character queryset is empty: message + link to character creation
   - Two submit buttons: `Publish` (`action=publish`) / `Save draft` (`action=draft`)

### Phase 4 — Tests

1. `GET /games/compose/` → redirects to login if anonymous
2. `GET /games/compose/?character=<slug>` → 200, character pre-selected
3. `POST` valid → report created with correct game, language, `ReportCast(role=MAIN)`, redirects
4. `POST` with character belonging to another user's game → 404
5. `POST` missing content → re-renders form with error
6. `GET /games/compose/` with no eligible characters → 200, empty state message rendered

## Validation flow

1. Log in, go to `/games/compose/?character=<slug>`, verify character pre-selected
2. Fill content, publish → redirected to report detail, report visible
3. Save draft → report in draft state
4. Try with character from another user's game → 404
5. `make check` — all pass
