# Instruction: Markdown Editor — Frontend (EasyMDE + Alpine component)

## Feature

- **Summary**: Install EasyMDE, create a `markdownEditor` Alpine.data component that initializes EasyMDE and integrates @mention support via CodeMirror events
- **Stack**: `EasyMDE`, `Alpine.js 3.14`, `Vite`, `pnpm`
- **Branch name**: `feat/markdown-editor`
- **Parent Plan**: `./2026_04_29-markdown-editor-master.md`
- **Sequence**: `1 of 2`
- Confidence: 9/10
- Time to implement: 75min

## Existing files

- @frontend/src/main.js
- @frontend/package.json

## User Journey

```
N/A — frontend bundle change, no UI visible until Part 2
```

## Implementation phases

### Phase 1 — Install EasyMDE

1. `pnpm add easymde` in `frontend/`
2. Add import in `frontend/src/main.js`:
   - `import EasyMDE from 'easymde'`
   - `import 'easymde/dist/easymde.min.css'`

### Phase 2 — `markdownEditor` Alpine component

1. Add `Alpine.data('markdownEditor', (initialValue = '') => ({ ... }))` in `frontend/src/main.js` **after** `mentionInput` definition
2. Component structure:
   - `content`: string (synced from EasyMDE onChange)
   - `suggestions`, `showSuggestions`, `selectedIndex`, `_mentionStart`: same as `mentionInput`
   - `_easyMde`: EasyMDE instance reference
   - `dropdownStyle`: `{ top: '0px', left: '0px' }` (absolute position from `cursorCoords()`)
3. `init()` method (called automatically by Alpine when component mounts — no `x-init` needed):
   - Find `<textarea>` in `this.$el`
   - Initialize EasyMDE: `this._easyMde = new EasyMDE({ element: textarea, initialValue, spellChecker: false })`
   - Register `onChange`: sync `this.content = this._easyMde.value()`
   - Register CodeMirror `change` event: call `this._onCmChange()`
4. `_onCmChange()`: replaces `onInput` logic — reads text before cursor from `codemirror.getLine(cursor.line).slice(0, cursor.ch)`, detects `@`, fetches suggestions (same API as `mentionInput`)
5. `_getDropdownPosition()`: uses `codemirror.cursorCoords(true, 'window')` (viewport-relative, required for `position: fixed`) → sets `dropdownStyle` with `top`/`left` values
6. `selectSuggestion(s)`: uses `codemirror.replaceRange(mention, from, to)` instead of textarea cursor manipulation
7. `onKeydown`: unchanged logic (arrow keys + enter/escape on dropdown)

### Phase 3 — Cleanup

1. Remove `Alpine.data('mentionInput', ...)` from `frontend/src/main.js` — no longer used after Part 2 replaces all templates

### Phase 4 — Build

1. `pnpm run build` in `frontend/`
2. Verify `static/dist/js/main.js` and `static/dist/css/` updated
3. Verify `mentionInput` is absent from the built bundle

### Phase 4 — Tests

1. No automated tests for frontend JS — manual validation at checkpoint:
   - EasyMDE editor renders in isolation (can test with a simple HTML file if needed)
   - `@` triggers suggestion fetch and dropdown appears at cursor position
   - Selecting a suggestion inserts it correctly
   - `easyMde.value()` returns Markdown content (not HTML)

## Validation flow

1. `pnpm run build` completes without errors
2. Open Django dev server, navigate to `/games/compose/`
3. EasyMDE editor renders with toolbar
4. Type `@` → suggestions dropdown appears near cursor
5. Select suggestion → `@charactername` inserted in editor
6. Submit form → backend receives Markdown content in `request.POST['content']`
