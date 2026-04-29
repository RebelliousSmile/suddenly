# Instruction: Markdown Editor — Templates integration

## Feature

- **Summary**: Update `report_editor.html` shared component to use `markdownEditor`, replace inline textarea blocks in both report forms with `{% include %}`
- **Stack**: `Django templates`, `Alpine.js`, `HTMX`
- **Branch name**: `feat/markdown-editor`
- **Parent Plan**: `./2026_04_29-markdown-editor-master.md`
- **Sequence**: `2 of 2`
- Confidence: 9/10
- Time to implement: 30min

## Existing files

- @templates/components/report_editor.html
- @templates/games/report_compose.html
- @templates/games/report_create.html

## User Journey

```
User opens report form
        ↓
EasyMDE editor renders (toolbar + editor pane)
        ↓
User types @ → suggestion dropdown appears at cursor
        ↓
User selects character → @mention inserted
        ↓
User submits → Markdown content POSTed as "content" field
```

## Implementation phases

### Phase 1 — Update shared component

1. Rewrite `templates/components/report_editor.html`:
   - Outer div: `x-data="markdownEditor('{{ initial_content|escapejs }}')"` — `escapejs` applied in the component, not in the calling template (XSS-safe)
   - Keep `<textarea id="content" name="content">` (EasyMDE wraps it)
   - Replace mention suggestions div: use `x-show="showSuggestions"` with `position: fixed` and `:style="dropdownStyle"` (coords from `cursorCoords(true, 'window')` — viewport-relative, correct with fixed positioning)
   - Remove `x-model`, `@input`, `@keydown` — those move into the Alpine component `init()`
   - Keep `<p class="form-help">` hint about Markdown + @mentions

### Phase 2 — Replace inline blocks in forms

1. In `report_compose.html`: replace the entire `x-data="mentionInput(...)"` div block with:
   `{% include "components/report_editor.html" with initial_content=form_data.content|default:'' only %}`
2. In `report_create.html`: same replacement
   (Note: `only` keyword isolates the include context — `initial_content` is the only variable passed; `escapejs` is applied inside the component template)

### Phase 3 — Tests

1. `GET /games/compose/` → EasyMDE renders, no JS errors in console
2. `GET /games/<pk>/reports/new/` → same
3. POST both forms with content → `request.POST['content']` contains Markdown (not HTML)
4. Re-open a draft report → initial content pre-filled in editor

## Validation flow

1. Navigate to `/games/compose/`, verify EasyMDE toolbar visible
2. Write Markdown (`**bold**`, `# title`) → preview renders correctly
3. Type `@` → dropdown appears at cursor position (not at top-left corner)
4. Select a character → mention inserted at cursor
5. Submit → report saved with Markdown content
6. Re-open draft → content pre-filled
7. Repeat on `/games/<pk>/reports/new/`
