---
name: 'custom:03:site_section'
description: 'Plan and implement a new or modified section on the marketing site'
argument-hint: 'Description of the section to add or modify (page, content, purpose)'
---

# Site Section

## Goal

Plan and implement a section on the marketing site based on this request:

```text
$ARGUMENTS
```

## Context

### Design system

```markdown
[aidd_docs/memory/internal/design.md](../../../memory/internal/design.md)
```

### Project structure

```markdown
[aidd_docs/memory/codebase_map.md](../../../memory/codebase_map.md)
```

## Rules

- UI language is **French** — all copy must be written in French
- Use **only** UnoCSS utility classes — no inline styles unless a value has no UnoCSS equivalent
- Use design system tokens from `uno.config.ts` (e.g. `text-ink`, `bg-surface`, `border-sep`)
- Follow existing section patterns from the target page (spacing, card style, icon style)
- No new dependencies — the stack is Nuxt + Vue + UnoCSS, keep it that way
- Keep components in the page file unless reuse is explicit

## Steps

### Step 1 — Clarify

1. Identify the target page (`/`, `/features`, `/about`)
2. Clarify the section purpose: what does it communicate to the visitor?
3. Clarify placement: where in the page (before/after which existing section)?
4. Clarify content: heading, body copy, CTA if any, visual element (icon, mockup, diagram)?
5. If anything is ambiguous, **ask before proceeding**

### Step 2 — Audit existing patterns

6. Read the target page file to understand existing structure and patterns
7. Identify which existing section is closest in style to what's needed
8. Note the exact UnoCSS classes used for spacing, typography, and layout in that section

### Step 3 — Plan

9. Define the section structure (HTML hierarchy + components)
10. List the UnoCSS classes to use for each element
11. Write the French copy (heading, subheading, body, CTA label if applicable)
12. **Display the plan and wait for approval before writing any code**

### Step 4 — Implement

13. Insert the section in the target page at the correct position
14. Use Vue `v-for` / `v-if` only when genuinely needed — prefer static markup for static content
15. Inline SVG icons following the pattern of existing sections (stroke-based, consistent sizing)

### Step 5 — Validate

16. Run `pnpm run build` to verify no build errors
17. List visual elements to check (responsive layout, color contrast, text legibility)
18. Invoke `@iris` to verify UI conformity against the plan
