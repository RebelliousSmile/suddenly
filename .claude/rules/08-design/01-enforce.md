---
paths:
  - "templates/**/*.html"
  - "frontend/src/**/*.js"
---

# Design system gate (enforce)

Contract: `design/tokens.json` + `design/components.json` (mode `utility-first`, frozen by `design:adjust`).

## Before generating HTML or utility classes

- Colour utilities (`bg-`/`text-`/`border-`/`ring-`/`outline-`/`from-`/`to-`/`via-`/`fill-`/`stroke-`/`decoration-`/`accent-`) resolve only to `color.*` namespaces: `brand`, `neutral`, `sepia`, `semantic`, `ui`, `domain`
- Never a Tailwind default palette (`amber-*`, `green-*`, `blue-*`, `red-*`, …) — those are out of contract
- No raw hex in `style="…"` or `<style>` blocks — use `var(--…)` tokens
- `var(--…)` references must match a token path in `tokens.json`
- Enrich layout with `@container app (min-width: …)`, never `@media` (cf. `mobile-first.md`)

## Pivot-only rules (AST — enforced by sc-js:design-bridge, not the string linter)

- State never by colour alone: status = icon + text/aria
- Decorative icon → `aria-hidden="true"`; meaningful icon → accessible name
- Touch targets ≥ 44×44 px (`--size-tap`)
- Icons from Lucide only; never emoji as UI glyph

## Verify

- `node design/lint/lint-files.mjs <files>` exits 0 before commit
- Adding a class/token: re-freeze via `/design:adjust`, then re-run `/design:enforce`

## Exemptions (documented in `design/lint/.lintrc.json § _exclude`)

- `templates/wireframes/**` — pre-manifest prototyping mockups, not served
- `templates/500.html` — standalone error page, inline hex load-bearing (tokens.css may be down)
