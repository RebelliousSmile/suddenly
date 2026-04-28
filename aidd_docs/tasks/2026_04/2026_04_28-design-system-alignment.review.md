---
name: code-review
description: Code review checklist and scoring template
argument-hint: N/A
---

# Code Review for feat/design-system — Design System Alignment (Dark Cosmos)

This branch migrates the Suddenly design system from a light-mode indigo/emerald/amber palette to a "dark cosmos" theme centered on deep purples (`#0a0915`) and crimson (`#e03558`). 67 files changed (587 insertions, 606 deletions).

- Status: APPROVED WITH RESERVATIONS
- Confidence: HIGH

---

- [Main expected Changes](#main-expected-changes)
- [Scoring](#scoring)
- [Code Quality Checklist](#code-quality-checklist)
  - [Potentially Unnecessary Elements](#potentially-unnecessary-elements)
  - [Standards Compliance](#standards-compliance)
  - [Architecture](#architecture)
  - [Code Health](#code-health)
  - [Security](#security)
  - [Error management](#error-management)
  - [Performance](#performance)
  - [Frontend specific](#frontend-specific)
- [Final Review](#final-review)

## Main expected Changes

- [x] `uno.config.js` — palette reworked to dark cosmos tokens
- [x] `base.css` — body background and color set for dark mode
- [x] Templates — systematic replacement of `text-gray-*`, `bg-white`, `border-gray-*` with semantic tokens
- [x] Button shortcuts redesigned (standalone, no more `btn` base)
- [x] Badge shortcuts updated to dark-friendly opacities
- [x] Prose, form, dropdown, link shortcuts aligned to new palette

## Scoring

- [🔴] **btn base class removed but still composed in templates** `templates/components/empty_state.html:23`, `templates/components/follow_button.html:24,38`, `templates/components/link_request_card.html:82,108` — `class="btn btn-primary btn-sm"` is used in 5 places. The `btn` shortcut no longer exists (it was replaced by the `btn-primary` / `btn-secondary` standalone shortcuts). These elements will render without the base flex/gap/transition styles. (Remove `btn` from all those class attributes — `btn-primary` is now self-contained.)

- [🔴] **Opacity modifier classes missing from safelist** `frontend/uno.config.js:201+` — Alpine.js `:class` bindings in `templates/base.html:208-210` use `bg-success/10`, `bg-error/10`, `bg-info/10`, `border-success/30`, `border-error/30`, `border-info/30` dynamically at runtime. UnoCSS cannot scan JavaScript string expressions. These six classes are absent from the safelist. The flash banners will render without background color in production. (Add these classes to the safelist, alongside the existing `badge-*` entries.)

- [🔴] **Old scale-based tokens still referenced in 6 templates** — The `secondary-*` and `primary-*` color scales were removed from the theme but are still used in templates:
  - `templates/core/home.html` — `bg-gradient-to-b from-primary-50 to-white`, `bg-secondary-100`, `text-secondary-600`
  - `templates/characters/link_choose_type.html` — `bg-secondary-100 text-secondary-600`, `bg-violet-100 text-violet-600`
  - `templates/characters/link_request_accepted.html` — `text-secondary-500`
  - `templates/characters/link_request_form.html` — `bg-secondary-100 text-secondary-600`, `bg-violet-100 text-violet-600`
  - `templates/characters/link_request_sent.html` — `text-secondary-500`
  - `templates/components/character_card.html` — `text-secondary-600 hover:bg-secondary-50`, `text-violet-600 hover:bg-violet-50`
  
  These classes will resolve to nothing since the scales no longer exist in the theme. (Replace with tokens from the new palette: `text-secondary`, `bg-surface`, `bg-indigo-900/40`, etc.)

- [🟡] **Hardcoded hex values in base.css instead of tokens** `frontend/src/base.css:2-4` — `background: radial-gradient(ellipse at top, rgba(24,18,40,0.5), #0a0915) #0a0915` and `color: #ede8f5` are hardcoded hex values. `#0a0915` corresponds to the `background` token and `#ede8f5` to the `primary` token defined in `uno.config.js`. This creates two sources of truth — if either token changes, base.css must be updated manually. (Reference CSS custom properties via `@apply` or use `var(--un-color-background)` if exposed, or at minimum add a comment linking to the token source.)

- [🟡] **Hardcoded hex in htmx-indicator.css** `frontend/src/htmx-indicator.css:12` — `background-color: #e03558` is the hardcoded crimson value. Same dual-source-of-truth issue as above. (Use a CSS variable or add a comment `/* = theme.colors.crimson.DEFAULT */`.)

- [🟡] **Hardcoded hex in presetTypography cssExtend** `frontend/uno.config.js:178,184` — `'color': '#e03558'` and `'border-left-color': '#e03558'` are hardcoded. UnoCSS presetTypography `cssExtend` does not support theme token resolution, so this is a known limitation — but it should be documented with a comment indicating this is `colors.crimson.DEFAULT`. (Add inline comment to signal it must be updated when the token changes.)

- [🟡] **`btn-lg` / `btn-sm` composition creates padding conflicts** `frontend/uno.config.js:100,101` — `btn-primary` now hardcodes `px-7 py-[13px]`, while `btn-lg` adds `px-6 py-3` and `btn-sm` adds `px-3 py-1.5`. In UnoCSS, the last class wins on conflicting utilities, so `btn-primary btn-sm` will apply `px-3 py-1.5` over the `px-7 py-[13px]` from `btn-primary`. This may or may not be the intended behavior for small primary buttons. The old architecture used `btn` (base) + `btn-primary` (color only) + `btn-sm` (sizing) which was cleaner. (Either document this override pattern explicitly, or switch `btn-primary` to carry only color/shadow/transition utilities and restore a base sizing layer.)

- [🟡] **Mixed border-radius conventions in shortcuts** `frontend/uno.config.js:88-164` — Some shortcuts use the `rounded-[12px]` arbitrary value (`btn-primary`, `btn-secondary`, `btn-danger`, `input-base`, `dropdown-menu`) while others use named tokens (`rounded-button`, `rounded-card`, `rounded-badge`). The `rounded-button` token is still defined in the theme but not always used. (Audit if `rounded-[12px]` equals `rounded-button` — if so, replace the arbitrary values with the token for DRY consistency.)

- [🟡] **`npc_highlight.html` mixes `border-amber-300` (Tailwind scale) with `bg-warning/10` (semantic token)** `templates/components/npc_highlight.html:12` — `border-amber-300` uses the raw Tailwind amber palette while the background uses the `warning` semantic token. On dark background, `amber-300` may work visually, but this breaks semantic consistency. (Replace `border-amber-300` with `border-warning/50` or `border-warning` to align with the semantic token pattern used elsewhere.)

- [🟡] **`notification_item.html` mixes old Tailwind classes with new tokens** `templates/components/notification_item.html:27,32` — `bg-emerald-100 text-emerald-600` and `bg-violet-100 text-violet-600` are light-mode classes that will look incorrect on the dark cosmos background. The `link_accepted` and `shared_sequence` notification types were not migrated. (Replace with dark-appropriate equivalents: `bg-emerald-900/40 text-emerald-400` and `bg-violet-900/40 text-violet-400`, consistent with the badge pattern used in `uno.config.js`.)

- [🟡] **`notifications/_items.html` has the same issue** `templates/notifications/_items.html` — same emerald/violet light-mode classes as `notification_item.html`.

- [🟢] No `style=""` inline styles introduced in any template
- [🟢] Safelist covers all dynamically generated badge-* status classes
- [🟢] Font migration (Lora → Crimson Text) consistent in both `uno.config.js` and `base.html` font link
- [🟢] Body background/color removed from `<body>` class attribute and moved to `base.css` — correct separation
- [🟢] All message flash classes use semantic tokens (`bg-success/10`, `text-success`, `border-success/30`)
- [🟢] Opacity modifiers that appear as static strings in template conditionals (`{% if %}` blocks) are scannable by UnoCSS since they are literal strings in the filesystem
- [🟢] Shadow tokens (`card`, `card-hover`, `dropdown`, `btn`) remain properly defined
- [🟢] Z-index tokens unchanged and correct in safelist
- [🟢] `prose-report` correctly migrated from `prose-indigo` to `prose-invert` for dark mode
- [🟢] No SQL/XSS/auth surface introduced — purely presentational changes
- [🟢] `input-base` shortcut added for consistent form input styling

## Code Quality Checklist

### Potentially Unnecessary Elements

- [🟡] `btn-lg` and `btn-sm` exist as sizing modifiers but the new `btn-primary` / `btn-secondary` shortcuts are not designed to be composed with them (they bake in their own padding). These size modifiers are now partially orphaned except when used with `btn-ghost`. Review if `btn-lg` is actually used anywhere — if not, remove.

### Standards Compliance

- [🟢] Naming conventions followed (token names: background, surface, card, border, primary, secondary, muted, crimson — all semantic and consistent)
- [🟡] `transition-all duration-250` in btn shortcuts — `duration-250` is non-standard Tailwind/UnoCSS (standard values are 150, 200, 300, etc.). Verify this generates valid CSS or define it as a custom duration token.

### Architecture

- [🟢] Design patterns respected — UnoCSS shortcuts remain the authoritative source for component classes
- [🟡] `base.css` now has functional styles (`body {}`) rather than being a pure reset/overrides file. The comment explaining its purpose was removed. (Restore or update the comment to clarify the file's role.)

### Code Health

- [🟢] Token vocabulary is well-defined and consistently applied across the new files
- [🔴] 6 templates reference deleted color scales (`primary-50`, `secondary-100`, `secondary-500`, `secondary-600`) — dead token references
- [🔴] 5 template locations use the removed `btn` base shortcut

### Security

- [🟢] No new SQL injection, XSS, or auth surface
- [🟢] No new environment variable exposure
- [🟢] No CORS configuration changes

### Error management

- [🟢] Error state classes (`bg-error/10`, `text-error`) consistently applied across flash messages and form error contexts

### Performance

- [🟢] Moving from a 10-shade scale per color to flat tokens reduces the number of generated CSS classes significantly — smaller bundle expected
- [🟢] Safelist remains minimal and targeted

### Frontend specific

#### State Management

- [🟢] Loading states: htmx indicator updated with crimson color
- [🟢] Empty states: component uses new token classes
- [🟡] Error states in notification_item partially migrated (link_accepted and shared_sequence still use light-mode classes)
- [🟢] Success feedback: flash message system correctly updated

#### UI/UX

- [🟡] Light-mode remnants in 6 templates will create jarring contrast issues on the dark cosmos background (white/light-gray backgrounds on dark page)
- [🟢] Consistent use of `text-primary`, `text-secondary`, `text-muted` hierarchy across the migrated templates
- [🟢] Crimson used consistently as the accent/action color (CTA buttons, hover states, links, active indicators)
- [🟢] Semantic HTML unchanged — only class attributes modified

## Final Review

- **Score**: 6.5/10 — The overall direction is correct and well-executed for the migrated files. The dark cosmos token vocabulary is clean and semantically sound. However, three blocking issues prevent a merge-ready rating.

- **Feedback**: The palette refactor is architecturally coherent. The token system (`background`, `surface`, `card`, `border`, `primary`, `secondary`, `muted`, `crimson`, `error`, `warning`, `success`, `info`) is cleaner than the previous multi-scale approach. The main problem is incomplete migration: 6 templates still reference deleted color scales that will render broken in production (invisible or unstyled elements), the `btn` base class removal was not propagated to the 5 templates that still compose it, and 6 critical opacity modifier classes used in Alpine `:class` bindings are missing from the safelist and will be stripped from the production CSS bundle.

- **Follow-up Actions**:
  1. **BLOCKING** — Add to safelist: `bg-success/10`, `bg-error/10`, `bg-info/10`, `border-success/30`, `border-error/30`, `border-info/30` (used in Alpine `:class` in `base.html`)
  2. **BLOCKING** — Remove the `btn` class from `empty_state.html`, `follow_button.html`, `link_request_card.html` (5 occurrences total — `btn-primary` is now self-contained)
  3. **BLOCKING** — Migrate remaining old-scale references in `core/home.html`, `link_choose_type.html`, `link_request_accepted.html`, `link_request_form.html`, `link_request_sent.html`, `character_card.html`
  4. **SHOULD** — Migrate `notification_item.html` and `notifications/_items.html` emerald/violet light-mode classes to dark equivalents
  5. **SHOULD** — Replace `border-amber-300` in `npc_highlight.html` with `border-warning/50`
  6. **SHOULD** — Add comments in `base.css`, `htmx-indicator.css`, and `presetTypography` cssExtend linking hardcoded hex values to their token equivalents
  7. **COULD** — Verify `duration-250` generates valid CSS (standard breakpoints are 150/200/300); if not, define a custom `duration` token
  8. **COULD** — Audit whether `rounded-[12px]` equals `rounded-button` and consolidate to the token

- **Additional Notes**: The `text-muted` usage in templates (e.g. `class="text-muted"`) is valid — `muted` is now a color token, so UnoCSS will correctly generate `text-[#7a7290]`. The shortcut `'text-muted': 'text-gray-500'` was correctly removed since the token supersedes it. This is not a bug.
