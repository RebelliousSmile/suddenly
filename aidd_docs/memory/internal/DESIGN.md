---
name: design
description: Design system and UI guidelines
scope: frontend
---

# DESIGN.md

## Design Implementation

- **Design System Approach**: CSS variable-driven palette, adapts to light/dark via `[data-theme]` attribute, UnoCSS utility classes
- **Styling Method**: UnoCSS utility classes + CSS custom properties; `presetSuddenly` extends theme tokens

## Design System Files

- **Theme Config**: `frontend/uno.config.js` — `presetSuddenly` theme extension
- **CSS Variables**: `frontend/src/base.css` — `:root`, `[data-theme="light"]`, `[data-theme="dark"]`
- **Design Components**: `templates/components/` — server-rendered Django partials

## Color Palette

### Structural (CSS var, no opacity modifier)

- `background` → `--c-bg` (light: `#faf9f6`, dark: `#0b0705`)
- `surface` → `--c-surface` (light: `#f0ede8`, dark: `#170d08`)
- `card` → `--c-card` (light: `#ffffff`, dark: `#25150e`)
- `card.dark` → `--c-card-dark` (light: `#f5f2ec`, dark: `#1d0f09`)
- `border` → `--c-border` (light: `#d4cfe8`, dark: `#3d2215`)
- `primary` → `--c-primary` (light: `#1a1a2e`, dark: `#f0f0f0`)
- `secondary` → `--c-secondary` (light: `#555555`, dark: `#a0a0a0`)
- `muted` → `--c-muted` (light: `#8c8c8c`, dark: `#a0a0a0`)
- `input` → `--c-input-bg` (light: `#f0ede8`, dark: crimson tint)

### Action (RGB channels, supports opacity modifiers e.g. `bg-crimson/10`)

- `crimson` → danger/delete — `224 53 88`
- `violet` → link requests — `124 58 237`
- `neon` → publish/open — `0 230 118`
- `brand` → primary CTA, logo — `99 102 241` (`#6366f1`)

### Semantic Feedback

- `success` — light: green-700, dark: green-400
- `warning` — light: amber-700, dark: amber-400
- `error` — light: red-800, dark: red-300
- `info` — light: sky-700, dark: sky-400

## Typography

- `sans`: Inter, system-ui — body text
- `serif`: Crimson Text, Georgia — narrative/prose content
- `mono`: JetBrains Mono, Fira Code — code blocks
- Self-hosted via `static/fonts/*.woff2`, loaded via `templates/components/_fonts.html`

## Component Standards

### Buttons

- `btn-primary` — crimson fill, white text, rounded-[12px]
- `btn-secondary` — transparent, border, hover crimson
- `btn-ghost` — transparent, no border, subtle color shift
- `btn-danger` — error fill, white text
- Size modifiers: `btn-sm`, `btn-lg`

### Cards

- `card` — `bg-card border border-border rounded-2xl p-6`
- `card-hover` — card + hover shadow + crimson border tint + lift
- Sub-parts: `card-header`, `card-body`, `card-footer`

### Forms

- `form-input` — rounded-[12px], focus crimson border, bg-input
- `form-input-error` — error/10 background, error border
- Labels: `form-label`, help: `form-help`, error msg: `form-error`
- `form-select`, `form-dropzone`, `form-dropzone-link`
- Switch: `switch-track` + `switch-thumb` (replaces checkbox)

### Badges

- Base: `badge` — `inline-flex rounded-badge text-xs font-medium`
- Status badges: `badge-available` (neon), `badge-claimed` (info), `badge-adopted` (success), `badge-forked` (violet), `badge-pc` (brand), `badge-pending` (muted), `badge-rejected` (error), `badge-primary` (crimson), `badge-accent` (warning)

### Avatars

- `avatar-sm` (w-8), `avatar-md` (w-10), `avatar-lg` (w-12), `avatar-xl` (w-16)
- `avatar-placeholder` for missing images

### Available Components (`templates/components/`)

- `character_card.html` — character listing card with portrait
- `docs_sidebar.html` — documentation navigation sidebar
- `empty_state.html` — zero-data placeholder with game-icons
- `feed_item.html` — activity feed entry
- `follow_button.html` — follow/unfollow toggle
- `_fonts.html` — self-hosted font `<link>` tags
- `form_fields.html` — reusable form field macros
- `form_image_upload.html` — image upload with dropzone
- `form_switch.html` — toggle switch component
- `game_card.html` — game listing card
- `link_request_card.html` — character link request display
- `modal.html` — HTMX-compatible modal dialog
- `notification_item.html` — notification entry
- `npc_highlight.html` — NPC featured display
- `password_strength.html` — password meter
- `presence_indicator.html` — online/offline dot indicator
- `quote_card.html` — pull quote display
- `report_card.html` — report listing card
- `report_editor.html` — rich text report editing area
- `status_banner.html` — top-of-page status message
- `tag_filter.html` — tag-based filter chips

## Layout System

- **Rendering**: Django SSR, no SPA — HTMX partials replace sections
- **Container**: `container-app` — `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8`
- **Spacing token**: `safe` — `env(safe-area-inset-bottom)` for mobile

## Border Radius Tokens

- `rounded-card` — `0.75rem`
- `rounded-button` — `0.5rem`
- `rounded-badge` — `9999px`

## Z-Index Scale

- `z-dropdown` (10), `z-sticky` (20), `z-tooltip` (25), `z-overlay` (30), `z-modal` (40), `z-toast` (50)

## Animation

- Durations: `fast` 100ms, `normal` 200ms, `slow` 300ms
- Respects `prefers-reduced-motion` via CSS fallback

## Icons

- Lucide — UI icons (`i-lucide-*`)
- Simple Icons — brand logos (`i-simple-icons-*`)
- Game Icons — thematic empty states (`i-game-icons-*`)
- Scale 1.2×, `display: inline-block`, `vertical-align: middle`
