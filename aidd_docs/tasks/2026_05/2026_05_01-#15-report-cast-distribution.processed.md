---
name: plan
description: US-13 — Distribution/cast planning for a report before writing
---

# Instruction: US-13 — Report Cast Distribution

## Feature

- **Summary**: Allow a GM to define which characters (existing PC/NPC or new NPC on-the-fly) will appear in a report before writing it, with a role per character, so the editor can suggest @mentions from the cast. `report_compose` (quick one-shot) is out of scope — cast management targets the `report_create`/`report_edit` flow only.
- **Stack**: `Django 4.x`, `HTMX 1.9+` (django-htmx>=1.17), `EasyMDE`
- **Branch name**: `feat/us-13-report-cast-distribution`
- **Parent Plan**: `none`
- **Sequence**: `standalone`
- Confidence: 9/10
- Time to implement: 3-4h

## Existing files

- @suddenly/games/models.py (ReportCast, CastRole, Report)
- @suddenly/games/services.py (build_game_queryset — extend here)
- @suddenly/games/views.py (API publish action — source of publish logic)
- @suddenly/games/front_views.py (report_create, report_edit)
- @suddenly/games/front_urls.py
- @suddenly/characters/views.py (CharacterViewSet.search)
- @templates/games/report_form.html
- @static/js/components/markdownEditor.js (EasyMDE @mention autocomplete)

### New files to create

- `templates/games/_cast_entry.html` — HTMX fragment per cast row
- `templates/games/_cast_widget.html` — full cast section (list + add form)

## User Journey

```mermaid
flowchart TD
    A[GM opens New Report form] --> B[POST: create draft → redirect to report_edit]
    B --> C[Cast section visible above editor]
    C --> D{Add character}
    D -->|Existing| E[Search game chars, pick + role → cast_add POST]
    D -->|New NPC| F[Enter name + description + role → cast_add POST]
    E --> G[_cast_entry.html appended via HTMX beforeend]
    F --> G
    G --> C
    C --> H[GM writes content in EasyMDE]
    H --> I[@mention autocomplete → cast_mention_search → cast chars only]
    I --> J[GM publishes]
    J --> K[publish_report service: new NPCs persisted, CharacterAppearances created]
```

## Implementation phases

### Phase 1 — Publish service

> Extract NPC creation + CharacterAppearance logic into a reusable service function.

1. Add `publish_report(report: Report, user: User) -> Report` to `games/services.py`, wrapped in `transaction.atomic()`:
   - Iterate `report.cast.select_related("character")`: for entries where `is_new_character()`, create `Character` (name, description, status=npc, creator=user, origin_game=report.game)
   - `get_or_create` CharacterAppearance for each cast entry with resolved character
   - Set `report.status = PUBLISHED`, `report.published_at = now()`, `report.save(update_fields=[...])`
2. Replace inline publish block in `views.py` (API ViewSet `publish` action) with call to `publish_report(report, request.user)`
3. Replace inline publish blocks in `front_views.report_create` and `front_views.report_edit` with call to `publish_report(report, request.user)`

### Phase 2 — Cast management UI

> `report_create` redirects to edit after draft creation; the cast widget (HTMX) lives exclusively in `report_edit`.

**Change `report_create` flow:**
1. On POST success, after `Report.objects.create(...)`:
   - If action was `"publish"`: call `publish_report(report, request.user)` before redirecting
   - Always redirect to `report_edit` (instead of `report_detail`)
   - This gives the user the HTMX cast widget immediately after creation

**New HTMX endpoints in `front_views.py` (all `@login_required`, author-only):**
2. `cast_add(request, game_pk, pk)` — POST:
   - Accepts `character_slug` (optional), `new_character_name`, `new_character_description`, `role`
   - If `character_slug`: resolve Character from slug + guard it belongs to the game
   - Creates `ReportCast` entry; returns `_cast_entry.html` fragment (new entry in context)
   - Caller uses: `hx-target="#cast-list"` + `hx-swap="beforeend"`
3. `cast_remove(request, game_pk, pk, cast_pk)` — POST:
   - Deletes `ReportCast` entry; guards `report.author == request.user`
   - Returns `HttpResponse("")` (200 empty body)
   - Caller uses: `hx-target="#cast-entry-{{ entry.pk }}"` + `hx-swap="delete"` (HTMX 1.8+, confirmed safe)
4. `cast_character_search(request, game_pk)` — GET, `@login_required`:
   - Returns `JsonResponse([{"slug": ..., "name": ...}], safe=False)` filtered by `origin_game__pk=game_pk` + `name__icontains=q` (min 2 chars, limit 10)

**URLs — add to `front_urls.py`:**
5. ```python
   path("<uuid:game_pk>/reports/<uuid:pk>/cast/add/", front_views.cast_add, name="cast_add"),
   path("<uuid:game_pk>/reports/<uuid:pk>/cast/<uuid:cast_pk>/remove/", front_views.cast_remove, name="cast_remove"),
   path("<uuid:game_pk>/cast/search/", front_views.cast_character_search, name="cast_character_search"),
   path("<uuid:game_pk>/reports/<uuid:pk>/cast/mentions/", front_views.cast_mention_search, name="cast_mention_search"),
   ```

**Templates:**
6. Create `templates/games/_cast_entry.html`:
   - Root element: `<div id="cast-entry-{{ entry.pk }}" class="...">` (ID required for HTMX delete target)
   - Shows character name (`entry.character.name` or `entry.new_character_name`), role badge
   - Remove button: `hx-post="{% url 'games:cast_remove' game_pk=game.pk pk=report.pk cast_pk=entry.pk %}"` + `hx-target="#cast-entry-{{ entry.pk }}"` + `hx-swap="delete"`
7. Create `templates/games/_cast_widget.html`:
   - `<div id="cast-list">` — iterates `report.cast.all()` via `{% include "_cast_entry.html" %}`
   - Add form with **two distinct modes** toggled by radio/tabs:
     - Mode A "Existing character": character search input (calls `games:cast_character_search` for typeahead, populates hidden `character_slug` field) + role select
     - Mode B "New NPC": `new_character_name` text input + `new_character_description` textarea + role select
   - Single submit button for both modes: `hx-post="{% url 'games:cast_add' game_pk=game.pk pk=report.pk %}"` + `hx-target="#cast-list"` + `hx-swap="beforeend"`
8. Update `templates/games/report_form.html`:
   - Include `{% if report %}{% include "games/_cast_widget.html" %}{% endif %}` above the EasyMDE textarea

### Phase 3 — @mention scoped to cast

> When editing a report, restrict @mention autocomplete to the report's cast characters.

1. Add `cast_mention_search(request, game_pk, pk)` GET in `front_views.py` (`@login_required`, author-only):
   - Collects cast characters from `report.cast.select_related("character")`:
     - Existing chars: `{"name": entry.character.name, "slug": entry.character.slug}`
     - New NPC entries (`is_new_character()`): `{"name": entry.new_character_name, "slug": ""}` — no slug yet (not persisted); EasyMDE inserts `@name` directly
   - Filters by `q` (name icontains, min 2 chars)
   - Returns `JsonResponse([...], safe=False)`
2. In `report_form.html`, on the editor container div (when `report` is not None):
   ```html
   data-cast-mention-url="{% url 'games:cast_mention_search' game_pk=game.pk pk=report.pk %}"
   ```
3. In `markdownEditor.js` Alpine `init()`:
   - Read `const castUrl = this.$el.dataset.castMentionUrl`
   - If `castUrl` is present, replace the global `/api/characters/characters/search/` fetch URL with `castUrl` for the `@` trigger
   - EasyMDE inserts the `name` field from the response (works for both slug-bearing and slug-less entries)

## Validation flow

1. Navigate to existing game → New Report → fill title + content → Save as draft
2. Redirected to report_edit → cast section visible above editor
3. Mode A: search existing character in game → select + role "Supporting" → row appears via HTMX
4. Mode B: new NPC "Aldric" + description + role "Main" → row appears via HTMX
5. Click remove on a cast row → row disappears (hx-swap="delete")
6. Type `@Al` in editor → autocomplete lists "Aldric" only (not all chars)
7. Click Publish → verify in Django admin: "Aldric" Character (NPC) created, 2 CharacterAppearance rows
8. Verify `report_compose` unaffected (no cast section, no regression)
