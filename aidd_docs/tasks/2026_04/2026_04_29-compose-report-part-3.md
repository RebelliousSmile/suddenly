# Instruction: Characters list — "Commencer" button

## Feature

- **Summary**: Add a "Commencer" button at the top of the characters list that links to the compose page pre-filled with the user's first eligible character (one where `origin_game.owner = request.user`, non-remote). Visible only to authenticated users.
- **Stack**: `Django 4+`, `HTMX`, `UnoCSS`
- **Branch name**: `feat/compose-report`
- **Parent Plan**: `./2026_04_29-compose-report-master.md`
- **Sequence**: `3 of 3`
- Confidence: 9/10
- Time to implement: 20min

## Existing files

- @suddenly/characters/front_views.py
- @templates/characters/list.html

## User Journey

```
Characters list page (authenticated)
        ↓
"Commencer" button in header (top right, next to Select button)
        ↓
href="/games/compose/?character=<first_eligible_character_slug>"
        ↓
Compose page (Part 2)
```

## Implementation phases

### Phase 1 — View context

1. In `character_list()` (`suddenly/characters/front_views.py`):
   - Compute `first_character`: first item of the queryset filtered on `origin_game__owner=request.user, origin_game__remote=False` if user is authenticated, else `None`
   - Add `first_character` to the `htmx_render` context

### Phase 2 — Template

1. In `templates/characters/list.html`, inside the authenticated header block (next to the Select button):
   - Add "Commencer" button: `<a href="{% url 'games:compose' %}?character={{ first_character.slug }}" class="btn-primary btn-sm">` with `i-lucide-pen` icon
   - Show only if `first_character` is set: `{% if first_character %}`

### Phase 3 — Tests

1. `GET /characters/` authenticated with at least one eligible character → context contains `first_character`
2. `GET /characters/` authenticated with no eligible character → `first_character` is `None`, button not rendered
3. `GET /characters/` anonymous → no button rendered

## Validation flow

1. Log in, go to `/characters/`, verify "Commencer" button visible
2. Click "Commencer" → redirected to compose page with first character pre-selected
3. Log out, go to `/characters/` → no button
4. `make check` — all pass
