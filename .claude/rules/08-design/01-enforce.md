---
paths:
  - "templates/**/*.html"
  - "frontend/src/**/*.js"
---

# Design system gate (enforce)

Contract: `design/release.json` (format 2.0) roots `tokens.json` + `components.json` + `policies.json` (mode `utility-first`, frozen by `design:adjust`).

## Before generating HTML or utility classes

- Colour utilities (`bg-`/`text-`/`border-`/`ring-`/`outline-`/`from-`/`to-`/`via-`/`fill-`/`stroke-`/`decoration-`/`accent-`) resolve only to `color.*` namespaces: `brand`, `neutral`, `sepia`, `semantic`, `ui`, `domain`
- Never a Tailwind default palette (`amber-*`, `green-*`, `blue-*`, `red-*`, …) — those are out of contract
- No raw hex in `style="…"` or `<style>` blocks — use `var(--…)` tokens
- `var(--…)` references must match a token path in `tokens.json`
- Enrich layout with `@container app (min-width: …)`, never `@media` (cf. `mobile-first.md`)

## Rules with no realizer — hold them by hand

`run-gates.py` reports these 11 as `UNREALIZED`: declared in `policies.json § usage.rules[]`, never verified, never counted as a violation. No linter catches a breach.

- `state-colour-icon` — any `color.domain.*` state also carried by label or icon; covers character status, report kind, scene state
- `signal-never-text` — `color.brand.signal` fills only (1.6:1); availability text uses `color.domain.available-text`
- `display-font-is-fiction` — Fraunces/`font.family.display` for fiction content; chrome uses `font.family.sans`
- `focus-visible-required` — focus ring from `focus.*` group; never `outline:none` without replacement
- `tap-target-min` — interactive controls ≥ `size.tap` (44px) both dimensions
- `no-emoji-as-icon` — no emoji as icon, bullet, state pill or button glyph
- `icon-set-roles` — three disjoint sets: `lucide` all UI icons · `simple-icons` third-party logos only · `game-icons` decorative illustration only; brand/illustration icons never carry an action
- `icon-accessible-name` — decorative icon `aria-hidden="true"`; meaningful icon labelled; icon-only button always labelled
- `container-not-viewport` — `@container (app)` at `breakpoint.xs/sm/md`, never `@media`; `cqi` needs a named container
- `native-scales-not-overridden` — never inject `spacing`/`fontSize`/`lineHeight`/`letterSpacing`/`borderRadius`/`maxWidth` into the UnoCSS theme; keys collide with native scale (`p-4` would become 4px); consume via CSS var
- `wireframes-out-of-scope` — `templates/wireframes/*.html` are static mockups using native Tailwind colours, excluded from lint

## Verify

- `python design/lint/run-gates.py --config design/lint/gates.config.json` exits 0 before commit
- Same command runs as pre-commit hook `design-gates`
- A plan touching `templates/**` appends it to its `success_condition`
- Exit 1 = violation · exit 4 = contract below `validated`, conformity not assertable
- Single file, ad hoc: `node design/lint/lint-core.mjs <file> --contract design`
- Adding a class/token: re-freeze via `/design:adjust`, then re-run `/design:enforce`

## Scope of the green

- Literal `class="…"`, inline hex, `var(--…)` in scanned markup — nothing else
- Never covered: stylesheets, dynamic class bindings, ARIA, rendered contrast, cross-file consistency
- Contrast of declared pairs is measured at freeze, recorded in `release.json § checks.contrast`
- Known failing pairs are recorded in `release.json § gaps` — read them before picking a text colour

## Exempt paths

Not enumerated in `design/lint/gates.config.json § targets`, so never linted:

- `templates/wireframes/**` — pre-manifest prototyping mockups, not served
- `templates/500.html` — standalone error page, inline hex load-bearing (tokens.css may be down)
