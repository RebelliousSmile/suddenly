---
description: Mobile-first / a11y design profile — smallest viewport as base, additive enrichment, no magic numbers, variant-based components, WCAG AA baseline, single icon set, no emoji.
paths: ["**/*.css", "**/*.html", "**/*.js", "design/**", "frontend/**", "templates/**"]
---

# Mobile-first / accessibility profile

Installed from `design:define` (profile-mobile-first). Binding conventions `enforce` can check.

## 1. Mobile-first authoring

- Base styles target the smallest viewport; no width query in the base layer; single column by default
- Enrich upward with `min-width` only; never `max-width` as the primary axis
- **This project enriches with `@container app (min-width: …)`, not `@media`** — the mockup drives layout by container width
- Breakpoints named from `design/tokens.json` (`breakpoint.xs/sm/md`); never ad-hoc; a breakpoint is justified by content, not by device
- Fluid by default: `clamp()` for type and spacing, relative units (`rem`, `%`, `fr`, `ch`, `cqi`), `max-width: 100%` on media
- Fluid type steps use `cqi` — they only resolve inside a named container context

## 2. Progressive enhancement (≥ tablet/desktop)

- Mobile core completes the task alone; enrichment is **additive, never load-bearing**
- Never lock a required action behind a breakpoint; never hide critical content on mobile
- Enrichment may add: side rails, persistent nav, dense tables, multi-column galleries, hover affordances
- Same content model at every breakpoint — only density and affordance change
- No `display:none` on content useful to a mobile user or a crawler

## 3. Mobile-only UX

- Every mobile-only pattern **declares its desktop equivalent**; replace, never duplicate; identical task outcome
- Sanctioned pairs: bottom sheet → side panel; sticky thumb CTA / bottom bar (`actionbar`) → top nav; swipe/carousel → grid or arrow rail; accordion → columns
- Switch at the breakpoint, never by user-agent sniffing; every touch gesture has a visible fallback

## 4. Token discipline

- `design/tokens.json` is canonical (W3C DTCG); consume through `design/adapters/tokens.css` (CSS vars) or `design/adapters/uno-tokens.mjs` (UnoCSS theme)
- Never edit generated adapters; regenerate both together after a token change
- **No magic number**: color, type, space, radius, shadow, motion come from tokens; no inline hex, no hard-coded px
- A one-off value is a new token, not an inline literal
- Prefer semantic tokens over raw ramps in components (`--color-surface`, not `--color-neutral-200`); name by role (`danger`, not `red`)
- `color.domain.*` encodes narrative state (pc / npc / available / remote / claimed / adopted / forked) — never repurpose these for decoration

## 5. Reusable components with variants

- Extend by option, never fork; one component, one responsibility; no copy-paste to change a value
- Variant = named visual mode (`primary`, `secondary`, `ghost`); size = scale step (`sm`/`md`); booleans for additive features
- Defaults usable with no props

## 6. Accessibility baseline

- Body text WCAG AA (4.5:1); large text and UI elements 3:1; never state by color alone
- Visible focus on every focusable element; keyboard-reachable interactives; logical tab order
- Touch targets ≥ 44×44 px (`--size-tap`); primary mobile actions within thumb reach
- Honour `prefers-reduced-motion`; meaningful `alt` (empty if decorative); one `<h1>` per page; landmarks (`header`/`nav`/`main`/`footer`)
- Button for action, link for navigation; every form control labelled

## 7. Iconography

- All UI icons come from **Lucide**, outline style, `stroke-width: 2` — never mix sets
- Size from `icon.size.*`, stroke from `icon.stroke.*`; color via `currentColor` or a semantic token; no hard-coded dimensions
- **Never an emoji** as UI icon, bullet, status dot or button glyph — emoji are user content, not the system's visual language
- A status = icon + text/aria, never icon alone
- Decorative icon → `aria-hidden="true"`; meaningful icon → accessible label; icon-only button always labelled
