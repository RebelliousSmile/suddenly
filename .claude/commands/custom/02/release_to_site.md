---
name: 'custom:02:release_to_site'
description: 'Translate an email2markdown app release into marketing content updates on the site'
argument-hint: 'Release tag (e.g. v1.2.0) — omit for latest release'
---

# Release to Site

## Goal

Fetch a release from the email2markdown app repository and translate notable changes into marketing content updates on this site.

```text
$ARGUMENTS
```

## Context

### Project brief

```markdown
[aidd_docs/memory/project_brief.md](../../../memory/project_brief.md)
```

### Design system

```markdown
[aidd_docs/memory/internal/design.md](../../../memory/internal/design.md)
```

## Rules

- App repository: `RebelliousSmile/email2markdown.app` — use `gh` CLI to fetch release data
- UI language is **French** — all copy must be written in French
- Only surface changes that matter to a **non-technical visitor** — ignore refactors, CI fixes, internal tooling
- Do not invent or embellish — stay strictly faithful to what the release notes say
- Prefer updating existing sections over creating new pages unless the change is major enough
- Use UnoCSS design tokens, no inline styles unless unavoidable

## Steps

### Step 1 — Fetch release data

1. Run the appropriate `gh` command to fetch the release:
   - If argument provided: `gh release view $ARGUMENTS --repo RebelliousSmile/email2markdown.app`
   - If no argument: `gh release list --repo RebelliousSmile/email2markdown.app --limit 1` then fetch it
2. Extract: tag, date, title, body (full release notes)

### Step 2 — Parse and classify changes

3. Read the release body and extract individual changes
4. Classify each change:

   | Category | Examples | Surface on site? |
   |---|---|---|
   | **New feature** | New CLI command, new export format | ✅ Yes |
   | **Notable improvement** | Faster export, better Markdown output | ✅ Yes |
   | **UX change** | New systray menu item, better error messages | ✅ Yes |
   | **Bug fix** | Only if user-visible and significant | ⚠️ Sometimes |
   | **Internal** | Refactor, CI, deps update | ❌ No |

5. List only the changes that will be surfaced, with a one-line French summary for each

### Step 3 — Map changes to site pages

6. For each surfaced change, determine the site impact:
   - **`/features`** — update an existing feature section or add a new one
   - **`/`** — update a feature card or flow diagram if something fundamental changed
   - **New page** — only if the change is major enough (e.g. entirely new product capability)
7. **Display the mapping and proposed copy — wait for approval before writing any code**

### Step 4 — Implement

8. Apply the approved changes page by page
9. Follow existing section patterns for any new content (spacing, icon style, French tone)
10. If a new section is added to `/features`, maintain the alternating grid layout pattern

### Step 5 — Validate

11. Run `pnpm run build` to verify no build errors
12. Summarize what was changed and on which pages
13. Suggest a commit message following the project VCS convention:
    ```
    content(features): update for release $VERSION
    ```
