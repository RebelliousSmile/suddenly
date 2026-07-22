---
name: design
description: Design system and UI guidelines — contract-driven
scope: frontend
---

# DESIGN.md

## Source of truth — the contract, not this file

- Canonical: `design/tokens.json` (values) · `design/components.json` (closed vocabulary) · `design/design-system.md` (charter)
- This file is a pointer + the delta between contract and shipped code. It never restates token values
- Never hand-edit `design/adapters/*` — generated from `tokens.json`
- Contract v1.0.0, `mode: utility-first` — closed vocabulary applies to **token usage**, not BEM class names

## Migration DONE — contract is frozen (v1.0.0)

- 6303 occurrences migrated across 147 files. The flat namespaces (`text-muted`, `bg-crimson`, `--c-*`) **no longer exist** — do not reintroduce them
- Colour utilities: head segment MUST be a top-level group of `tokens.json § color.*` — `brand`, `neutral`, `sepia`, `semantic`, `domain`, `ui`

| Namespace | Use |
|---|---|
| `text-semantic-ink` / `-ink-secondary` / `-muted` | text, in decreasing prominence |
| `bg-semantic-background` / `-surface` / `-card` / `-card-sunken` | grounds |
| `border-semantic-border` | borders |
| `bg-brand-primary` (+ `/10`) / `-primary-hover` | primary action (crimson) |
| `text-brand-accent` | federation, fork, oracle (violet) |
| `bg-brand-signal` (surfaces only) | availability signal (neon) |
| `text-domain-available-text` | availability **text** — never `brand-signal` on a glyph |
| `text-domain-pc` / `-npc` / `-claimed` / `-adopted` / `-forked` | narrative status |
| `text-semantic-danger` / `-success` / `-warning` / `-info` | feedback |
| `bg-ui-sun` / `border-ui-sun-soft` | theme-switch iconography only |
| `var(--color-semantic-muted)` … | CSS vars, from `design/adapters/tokens.css` |

## Colour carries domain meaning — not decoration

- `color.domain.*` encodes narrative state; never repurpose for styling
- `pc` = indigo `#6366f1` · `npc` = amber `#b45309` · `available` = neon `#00e676` · `remote`/`forked`/`oracle` = violet `#7c3aed` · `claimed` = blue · `adopted` = green
- **`brand.signal` (#00e676) never carries a glyph** — 1.6:1 on light ground. Text uses `domain.available-text` (`#0a8f4d`). Rule: `usage.rules[signal-never-text]`
- A status is never colour-only: it pairs a `color.domain.*` token with a label or icon; avatar rings add a distinct `border.style`

## Shipped code — what is actually true today

- Tokens live in `design/adapters/tokens.css` (generated), imported by `main.js` **before** `base.css`. `base.css` holds only reset + page decoration + native control styling
- Each colour is emitted twice: `--color-x` (hex) and `--color-x-rgb` (channels) — the latter is what makes `bg-brand-primary/10` work
- Crimson is the **primary action** (`btn-primary`); danger is `semantic-danger` (`btn-danger`). Older docs claiming `crimson = danger/delete` are wrong
- Theme switch via `[data-theme="light"|"dark"]` on the root element
- Dark mode is **sepia** (`#0b0705` → `#25150e`), not neutral black. Docs showing `#0a0a0a`/`#111111` are stale
- `focus-ring` shortcut carries the frozen focus (2px, offset 2px, indigo) — apply it to every interactive control

## Typography — Fraunces (fiction) + Inter (chrome)

- `sans` **Inter** — self-hosted 400/500/600/700. All chrome
- `serif` / `display` **Fraunces** — self-hosted VARIABLE font: `fraunces-var.woff2` (roman) + `fraunces-var-italic.woff2` (italic), latin subset, weights 400–700, optical axis `opsz`
- Both `font-serif` and `font-display` resolve to Fraunces — no need to rename existing `font-serif` usages
- **Crimson Text was removed** (v1.1.0). Do not reintroduce it
- `mono` JetBrains Mono — NOT self-hosted, falls back to system mono
- Fonts declared in `templates/components/_fonts.html`, files in `static/fonts/*.woff2`
- The serif is reserved for fiction (narrative, descriptions, dialogue); the chrome uses Inter. **Italic serif marks narrative description — never plain emphasis** (`usage.rules[display-font-is-fiction]`)
- `SOFT` and `WONK` axes of Fraunces are available but unused

## Icons — three sets, three DISJOINT roles (`usage.rules[icon-set-roles]`)

- `i-lucide-*` — **every UI icon, no exception**. Outline, stroke 2. This IS the single UI set
- `i-simple-icons-*` — third-party platform/protocol logos ONLY (Mastodon, ActivityPub). A brand logo cannot be redrawn in lucide
- `i-game-icons-*` — decorative illustration ONLY (empty states, RPG register)
- **A `brand` or `illustration` icon NEVER carries an action** — no button, no link, no status badge. They illustrate; they do not drive
- BookWyrm has no simple-icons glyph → rendered with a `game-icons` book as a logo stand-in. Only tolerated exception, documented at the usage site
- **Never an emoji** as icon, bullet, status dot or button glyph
- Decorative icon → `aria-hidden="true"`; meaningful icon (replaces a word) → `aria-label`; icon-only button ALWAYS labelled (`usage.rules[icon-accessible-name]`)
- Known debt: ~1500 decorative lucide icons still lack `aria-hidden` (low impact — an empty `<span>` is not announced)

## Accessibility — frozen rules

- Focus: 2px outline, 2px offset, `color.semantic.focus` = indigo (NOT crimson — 4.2:1 is too low and would conflate focus with primary action). The v3 mockup had **zero** focus rules
- Touch targets ≥ `size.tap` (44px) on every interactive control
- `prefers-reduced-motion: reduce` zeroes all durations — carried by `adapters/tokens.css`, not by each component
- Known failures, unresolved at freeze: `semantic.muted` 3.2:1 · crimson-on-light text 4.2:1 · white-on-crimson 4.4:1

## Layout — container queries, NOT media queries

- Django SSR + HTMX partials. No SPA
- The `app` container is declared on `<body>` (`container-type: inline-size`) in `base.css`
- **Write `@sm:` / `@md:` / `@lg:` — never `sm:` / `md:` / `lg:`**. The bare form is a media query and bypasses the contract
- **`theme.containers` values MUST be full conditions**: `'(min-width: 640px)'`, never `'640px'`. UnoCSS interpolates them verbatim — `'640px'` yields `@container 640px{…}`, an INVALID at-rule the browser drops silently. Build stays green, no warning, and every grid collapses to one column. Only a DOM measurement catches it
- **A container measures available width, scrollbar excluded**: at a 768px viewport, `<body>` is ~752px on desktop, so `@md:` does NOT fire where `@media` did. Accepted consequence: a desktop window 768–784px wide shows the mobile layout. No effect on real mobile/tablet (overlay scrollbars)
- UnoCSS 0.62 marks the container-query variant **experimental** — not covered by semver. Verify by measurement after any upgrade
- `container-app` — `max-w-7xl mx-auto px-4 @sm:px-6 @lg:px-8`
- `spacing.safe` = `env(safe-area-inset-bottom)` — mobile action bar. Not a token; keep it

## Spacing — do not remap UnoCSS `spacing`

- Frozen scale is a **2px step** (`space.2` … `space.56`; keys are px values)
- UnoCSS's native scale already yields it via half-steps: `p-1.5` = 6px, `p-2.5` = 10px, `p-3.5` = 14px
- Remapping the `spacing` key would silently redefine `p-4` from 16px to 4px across every template. `uno-tokens.mjs` omits it on purpose

## Non-colour theme keys — migrated

- `rounded-card` → `rounded-xl` (12px) · `rounded-badge` → `rounded-full` · `rounded-button` → `rounded-lg` (8px)
- Native equivalences that match the contract: **`rounded-lg` = 8px** (`radius.md`, buttons/inputs), **`rounded-xl` = 12px** (`radius.lg`, cards/menus). Do NOT assume `rounded-md` is 8px — it is 6px
- `duration-normal` → `duration-base`; `duration-fast` is now 150ms (was 100ms), `duration-slow` 400ms (was 300ms)
- z-index **reordered**: `sticky(40) < header(50) < dropdown(60) < overlay(80) < modal(100) < toast(120)`. Dropdowns now sit above the sticky header — that is intended
- `shadow-btn` / `shadow-dropdown` have no token — kept as theme extension

## Components (`templates/components/`)

- Server-rendered Django partials: `character_card`, `game_card`, `report_card`, `feed_item`, `link_request_card`, `notification_item`, `npc_highlight`, `empty_state`, `modal`, `follow_button`, `presence_indicator`, `password_strength`, `status_banner`, `tag_filter`, `report_editor`, `docs_sidebar`, `_fonts`
- Form partials: `form_fields`, `form_image_upload`, `form_switch`
- The 17 BEM components in `design/components.json` (`rap`, `badge--npc`, `card__body`…) come from mockup v3 and are **not integrated yet** — declared ahead of use
