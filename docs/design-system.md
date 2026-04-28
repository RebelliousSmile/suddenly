# Design System

Suddenly's visual language — tokens, typography, and UI components for both light and dark modes.

---

## Moodboard

> **Sombre, littéraire, dramatique.** Typographie serif pour la narration, Inter pour l'interface. Les accents vifs (crimson, neon) émergent sur des fonds profonds comme des néons dans la nuit.

The two target aesthetics:

- **Dark** — deep cosmos background (`#0a0a0a`), surfaces slightly lifted (`#111111`), crimson glow on cards, neon green for success states.
- **Light** — warm parchment (`#faf9f6`), off-white cards, muted purple borders, crimson as primary accent.

---

## Palette & Tokens

### Semantic tokens (CSS variables)

| Token | Variable | Light | Dark |
|-------|----------|-------|------|
| Background | `--c-bg` | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#faf9f6;border:1px solid #ccc;vertical-align:middle;margin-right:4px"></span>`#faf9f6` | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#0a0a0a;border:1px solid #444;vertical-align:middle;margin-right:4px"></span>`#0a0a0a` |
| Surface | `--c-surface` | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#f0ede8;border:1px solid #ccc;vertical-align:middle;margin-right:4px"></span>`#f0ede8` | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#111111;border:1px solid #444;vertical-align:middle;margin-right:4px"></span>`#111111` |
| Card | `--c-card` | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#ffffff;border:1px solid #ccc;vertical-align:middle;margin-right:4px"></span>`#ffffff` | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#1a1a1a;border:1px solid #444;vertical-align:middle;margin-right:4px"></span>`#1a1a1a` |
| Card dark variant | `--c-card-dark` | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#f5f2ec;border:1px solid #ccc;vertical-align:middle;margin-right:4px"></span>`#f5f2ec` | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#222222;border:1px solid #444;vertical-align:middle;margin-right:4px"></span>`#222222` |
| Border | `--c-border` | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#d4cfe8;border:1px solid #ccc;vertical-align:middle;margin-right:4px"></span>`#d4cfe8` | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#2a2a2a;border:1px solid #444;vertical-align:middle;margin-right:4px"></span>`#2a2a2a` |
| Primary text | `--c-primary` | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#1a1a2e;border:1px solid #ccc;vertical-align:middle;margin-right:4px"></span>`#1a1a2e` | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#f0f0f0;border:1px solid #444;vertical-align:middle;margin-right:4px"></span>`#f0f0f0` |
| Secondary text | `--c-secondary` | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#4a4a6a;border:1px solid #ccc;vertical-align:middle;margin-right:4px"></span>`#4a4a6a` | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#a0a0a0;border:1px solid #444;vertical-align:middle;margin-right:4px"></span>`#a0a0a0` |
| Muted text | `--c-muted` | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#8a8aaa;border:1px solid #ccc;vertical-align:middle;margin-right:4px"></span>`#8a8aaa` | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#606060;border:1px solid #444;vertical-align:middle;margin-right:4px"></span>`#606060` |

### Fixed accent colors

| Name | Hex | Usage |
|------|-----|-------|
| Crimson | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#e03558;vertical-align:middle;margin-right:4px"></span>`#e03558` | Primary CTA, links, focus rings — both modes |
| Crimson hover | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#c82a4a;vertical-align:middle;margin-right:4px"></span>`#c82a4a` | Button hover state |
| Violet | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#7c3aed;vertical-align:middle;margin-right:4px"></span>`#7c3aed` | Per-page accent (profile pages, nav active) |
| Neon | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#00e676;vertical-align:middle;margin-right:4px"></span>`#00e676` | Success / available states in dark mode |
| Success | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#16a34a;vertical-align:middle;margin-right:4px"></span>`#16a34a` | Positive feedback |
| Warning | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#d97706;vertical-align:middle;margin-right:4px"></span>`#d97706` | Caution states |
| Error | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#dc2626;vertical-align:middle;margin-right:4px"></span>`#dc2626` | Destructive actions, validation errors |
| Info | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#6366f1;vertical-align:middle;margin-right:4px"></span>`#6366f1` | Informational states |

### Swatches

<div class="sd-light">
<span class="sd-label">Light mode</span>
<div class="sd-row">
  <div class="sd-swatch"><span class="sd-swatch-color" style="background:#faf9f6"></span><span class="sd-swatch-name">bg<br>#faf9f6</span></div>
  <div class="sd-swatch"><span class="sd-swatch-color" style="background:#f0ede8"></span><span class="sd-swatch-name">surface<br>#f0ede8</span></div>
  <div class="sd-swatch"><span class="sd-swatch-color" style="background:#ffffff;border:1px solid #d4cfe8"></span><span class="sd-swatch-name">card<br>#ffffff</span></div>
  <div class="sd-swatch"><span class="sd-swatch-color" style="background:#d4cfe8"></span><span class="sd-swatch-name">border<br>#d4cfe8</span></div>
  <div class="sd-swatch"><span class="sd-swatch-color" style="background:#1a1a2e"></span><span class="sd-swatch-name">primary<br>#1a1a2e</span></div>
  <div class="sd-swatch"><span class="sd-swatch-color" style="background:#4a4a6a"></span><span class="sd-swatch-name">secondary<br>#4a4a6a</span></div>
  <div class="sd-swatch"><span class="sd-swatch-color" style="background:#8a8aaa"></span><span class="sd-swatch-name">muted<br>#8a8aaa</span></div>
  <div class="sd-swatch"><span class="sd-swatch-color" style="background:#e03558"></span><span class="sd-swatch-name">crimson<br>#e03558</span></div>
  <div class="sd-swatch"><span class="sd-swatch-color" style="background:#7c3aed"></span><span class="sd-swatch-name">violet<br>#7c3aed</span></div>
  <div class="sd-swatch"><span class="sd-swatch-color" style="background:#00e676"></span><span class="sd-swatch-name">neon<br>#00e676</span></div>
</div>
</div>

<div class="sd-dark">
<span class="sd-label">Dark mode</span>
<div class="sd-row">
  <div class="sd-swatch"><span class="sd-swatch-color" style="background:#0a0a0a;border-color:rgba(255,255,255,0.08)"></span><span class="sd-swatch-name" style="color:#606060">bg<br>#0a0a0a</span></div>
  <div class="sd-swatch"><span class="sd-swatch-color" style="background:#111111;border-color:rgba(255,255,255,0.08)"></span><span class="sd-swatch-name" style="color:#606060">surface<br>#111111</span></div>
  <div class="sd-swatch"><span class="sd-swatch-color" style="background:#1a1a1a;border-color:rgba(255,255,255,0.08)"></span><span class="sd-swatch-name" style="color:#606060">card<br>#1a1a1a</span></div>
  <div class="sd-swatch"><span class="sd-swatch-color" style="background:#2a2a2a;border-color:rgba(255,255,255,0.08)"></span><span class="sd-swatch-name" style="color:#606060">border<br>#2a2a2a</span></div>
  <div class="sd-swatch"><span class="sd-swatch-color" style="background:#f0f0f0"></span><span class="sd-swatch-name" style="color:#606060">primary<br>#f0f0f0</span></div>
  <div class="sd-swatch"><span class="sd-swatch-color" style="background:#a0a0a0"></span><span class="sd-swatch-name" style="color:#606060">secondary<br>#a0a0a0</span></div>
  <div class="sd-swatch"><span class="sd-swatch-color" style="background:#606060"></span><span class="sd-swatch-name" style="color:#606060">muted<br>#606060</span></div>
  <div class="sd-swatch"><span class="sd-swatch-color" style="background:#e03558"></span><span class="sd-swatch-name" style="color:#606060">crimson<br>#e03558</span></div>
  <div class="sd-swatch"><span class="sd-swatch-color" style="background:#7c3aed"></span><span class="sd-swatch-name" style="color:#606060">violet<br>#7c3aed</span></div>
  <div class="sd-swatch"><span class="sd-swatch-color" style="background:#00e676"></span><span class="sd-swatch-name" style="color:#606060">neon<br>#00e676</span></div>
</div>
</div>

---

## Typography

Three families — each with a distinct role:

| Family | Use | Weights |
|--------|-----|---------|
| **Inter** | UI — navigation, labels, buttons, body copy | 400, 500, 600, 700 |
| **Crimson Text** | Narrative — H1/H2/H3 headings, report prose, blockquotes | 400, 600, italic |
| **JetBrains Mono** | Code — inline and blocks | 400, 500 |

> **Rule**: Inter for all interface chrome. Crimson Text only where narrative voice matters — large headings and long-form text.

### Type scale — Light

<div class="sd-light">
<span class="sd-label">Light mode</span>
<p class="sd-h1 sd-typo-sample">H1 — Crimson Text 600, 2.25rem</p>
<p class="sd-h2 sd-typo-sample">H2 — Crimson Text 600, 1.6rem</p>
<p class="sd-h3 sd-typo-sample">H3 — Crimson Text 600, 1.25rem</p>
<p class="sd-h4 sd-typo-sample">H4 — Inter 600, 1rem</p>
<p class="sd-h5 sd-typo-sample">H5 — Inter 600, 0.875rem</p>
<p class="sd-h6 sd-typo-sample">H6 — Inter 600 caps, 0.8rem</p>
<hr style="border-color:#d4cfe8;margin:1rem 0">
<p class="sd-body   sd-typo-sample">Body — Inter 400, 1rem / 1.6. The characters mentioned can be claimed, adopted, or forked by other players.</p>
<p class="sd-small  sd-typo-sample">Small — Inter 400, 0.875rem. Secondary interface text, metadata, timestamps.</p>
<p class="sd-caption sd-typo-sample">Caption — Inter 400, 0.75rem. Helper text, image captions.</p>
<p class="sd-overline sd-typo-sample">Overline — Inter 600, 0.7rem, 3px tracking</p>
<hr style="border-color:#d4cfe8;margin:1rem 0">
<p class="sd-prose  sd-typo-sample">Prose — Crimson Text 400, 1.1rem / 1.7. The night was long and the fire had gone cold when the stranger finally appeared at the threshold.</p>
<p class="sd-prose-em sd-typo-sample">Prose italic — Crimson Text italic. "We do not choose our stories," she said, "they choose us."</p>
<hr style="border-color:#d4cfe8;margin:1rem 0">
<p class="sd-mono   sd-typo-sample">Mono — JetBrains Mono, 0.875rem. const actor = await federation.resolve(url);</p>
</div>

### Type scale — Dark

<div class="sd-dark">
<span class="sd-label">Dark mode</span>
<p class="sd-h1 sd-typo-sample">H1 — Crimson Text 600, 2.25rem</p>
<p class="sd-h2 sd-typo-sample">H2 — Crimson Text 600, 1.6rem</p>
<p class="sd-h3 sd-typo-sample">H3 — Crimson Text 600, 1.25rem</p>
<p class="sd-h4 sd-typo-sample">H4 — Inter 600, 1rem</p>
<p class="sd-h5 sd-typo-sample">H5 — Inter 600, 0.875rem</p>
<p class="sd-h6 sd-typo-sample">H6 — Inter 600 caps, 0.8rem</p>
<hr style="border-color:#2a2a2a;margin:1rem 0">
<p class="sd-body   sd-typo-sample">Body — Inter 400, 1rem / 1.6. The characters mentioned can be claimed, adopted, or forked by other players.</p>
<p class="sd-small  sd-typo-sample">Small — Inter 400, 0.875rem. Secondary interface text, metadata, timestamps.</p>
<p class="sd-caption sd-typo-sample">Caption — Inter 400, 0.75rem. Helper text, image captions.</p>
<p class="sd-overline sd-typo-sample">Overline — Inter 600, 0.7rem, 3px tracking</p>
<hr style="border-color:#2a2a2a;margin:1rem 0">
<p class="sd-prose  sd-typo-sample">Prose — Crimson Text 400, 1.1rem / 1.7. The night was long and the fire had gone cold when the stranger finally appeared at the threshold.</p>
<p class="sd-prose-em sd-typo-sample">Prose italic — Crimson Text italic. "We do not choose our stories," she said, "they choose us."</p>
<hr style="border-color:#2a2a2a;margin:1rem 0">
<p class="sd-mono   sd-typo-sample">Mono — JetBrains Mono, 0.875rem. const actor = await federation.resolve(url);</p>
</div>

---

## Buttons

| Class | Usage |
|-------|-------|
| `btn-primary` | Primary CTA — one per screen |
| `btn-secondary` | Secondary action alongside primary |
| `btn-ghost` | Tertiary / icon-only actions |
| `btn-danger` | Destructive actions (delete, reject) |
| `btn-sm` | Modifier — compact contexts |
| `btn-lg` | Modifier — hero sections |

<div class="sd-light">
<span class="sd-label">Light mode</span>
<div class="sd-row">
  <button class="sd-btn sd-btn-primary">Primary</button>
  <button class="sd-btn sd-btn-secondary">Secondary</button>
  <button class="sd-btn sd-btn-ghost">Ghost</button>
  <button class="sd-btn sd-btn-danger">Danger</button>
</div>
<div class="sd-row" style="margin-top:0.75rem">
  <button class="sd-btn sd-btn-primary sd-btn-sm">Small</button>
  <button class="sd-btn sd-btn-primary">Default</button>
  <button class="sd-btn sd-btn-primary sd-btn-lg">Large</button>
</div>
</div>

<div class="sd-dark">
<span class="sd-label">Dark mode</span>
<div class="sd-row">
  <button class="sd-btn sd-btn-primary">Primary</button>
  <button class="sd-btn sd-btn-secondary">Secondary</button>
  <button class="sd-btn sd-btn-ghost">Ghost</button>
  <button class="sd-btn sd-btn-danger">Danger</button>
</div>
<div class="sd-row" style="margin-top:0.75rem">
  <button class="sd-btn sd-btn-primary sd-btn-sm">Small</button>
  <button class="sd-btn sd-btn-primary">Default</button>
  <button class="sd-btn sd-btn-primary sd-btn-lg">Large</button>
</div>
</div>

---

## Badges

Character status badges — semantic colors consistent across both modes.

| Class | Meaning |
|-------|---------|
| `badge-available` | Character has no pending links |
| `badge-claimed` | Claim request pending or accepted |
| `badge-adopted` | Adoption accepted |
| `badge-forked` | Fork relationship established |
| `badge-pc` | Player Character (owned by a user) |
| `badge-pending` | Request awaiting response |
| `badge-rejected` | Request declined |

<div class="sd-light">
<span class="sd-label">Light mode</span>
<div class="sd-row">
  <span class="sd-badge sd-badge-available">Available</span>
  <span class="sd-badge sd-badge-claimed">Claimed</span>
  <span class="sd-badge sd-badge-adopted">Adopted</span>
  <span class="sd-badge sd-badge-forked">Forked</span>
  <span class="sd-badge sd-badge-pc">PC</span>
  <span class="sd-badge sd-badge-pending">Pending</span>
  <span class="sd-badge sd-badge-rejected">Rejected</span>
</div>
</div>

<div class="sd-dark">
<span class="sd-label">Dark mode</span>
<div class="sd-row">
  <span class="sd-badge sd-badge-available">Available</span>
  <span class="sd-badge sd-badge-claimed">Claimed</span>
  <span class="sd-badge sd-badge-adopted">Adopted</span>
  <span class="sd-badge sd-badge-forked">Forked</span>
  <span class="sd-badge sd-badge-pc">PC</span>
  <span class="sd-badge sd-badge-pending">Pending</span>
  <span class="sd-badge sd-badge-rejected">Rejected</span>
</div>
</div>

---

## Inputs

<div class="sd-light">
<span class="sd-label">Light mode</span>
<div class="sd-row" style="flex-direction:column;align-items:flex-start;gap:0.5rem">
  <label style="font-size:0.8125rem;font-weight:500;color:#4a4a6a;font-family:Inter,sans-serif">Character name <span style="color:#e03558">*</span></label>
  <input class="sd-input" type="text" placeholder="Enter a name…">
  <span style="font-size:0.75rem;color:#8a8aaa;font-family:Inter,sans-serif">The name as it appears in session reports.</span>
</div>
</div>

<div class="sd-dark">
<span class="sd-label">Dark mode</span>
<div class="sd-row" style="flex-direction:column;align-items:flex-start;gap:0.5rem">
  <label style="font-size:0.8125rem;font-weight:500;color:#a0a0a0;font-family:Inter,sans-serif">Character name <span style="color:#e03558">*</span></label>
  <input class="sd-input" type="text" placeholder="Enter a name…">
  <span style="font-size:0.75rem;color:#606060;font-family:Inter,sans-serif">The name as it appears in session reports.</span>
</div>
</div>

---

## Cards

<div class="sd-light">
<span class="sd-label">Light mode</span>
<div class="sd-card" style="max-width:320px">
  <p class="sd-card-title">Seraphina Voss</p>
  <p class="sd-card-body">NPC introduced in session 3. Former archivist, now rogue. Adopted by <a class="sd-link" href="#">@mireille</a>.</p>
  <div class="sd-row" style="margin-top:0.75rem">
    <span class="sd-badge sd-badge-adopted">Adopted</span>
    <span class="sd-badge sd-badge-pc">PC</span>
  </div>
</div>
</div>

<div class="sd-dark">
<span class="sd-label">Dark mode</span>
<div class="sd-card" style="max-width:320px">
  <p class="sd-card-title">Seraphina Voss</p>
  <p class="sd-card-body">NPC introduced in session 3. Former archivist, now rogue. Adopted by <a class="sd-link" href="#">@mireille</a>.</p>
  <div class="sd-row" style="margin-top:0.75rem">
    <span class="sd-badge sd-badge-adopted">Adopted</span>
    <span class="sd-badge sd-badge-pc">PC</span>
  </div>
</div>
</div>

---

## Links

| Class | Usage |
|-------|-------|
| `link` | Inline content links — crimson, underline on hover |
| `link-muted` | Subtle secondary links — muted, no underline |

<div class="sd-light">
<span class="sd-label">Light mode</span>
<div class="sd-row">
  <a class="sd-link" href="#">link — crimson</a>
  <a class="sd-link-muted" href="#">link-muted</a>
</div>
</div>

<div class="sd-dark">
<span class="sd-label">Dark mode</span>
<div class="sd-row">
  <a class="sd-link" href="#">link — crimson</a>
  <a class="sd-link-muted" href="#" style="color:#606060">link-muted</a>
</div>
</div>

---

## Theme Toggle

The pill switch in the top navigation — moon icon (dark) / sun icon (light).

<div class="sd-light">
<span class="sd-label">Light mode — sun active</span>
<div class="sd-row" style="align-items:center;gap:1rem">
  <div class="sd-toggle" title="Currently: light mode">
    <span class="sd-toggle-knob"></span>
  </div>
  <span style="font-size:0.8125rem;color:#4a4a6a;font-family:Inter,sans-serif">Amber knob slid right → light mode</span>
</div>
</div>

<div class="sd-dark">
<span class="sd-label">Dark mode — moon active</span>
<div class="sd-row" style="align-items:center;gap:1rem">
  <div class="sd-toggle" title="Currently: dark mode">
    <span class="sd-toggle-knob"></span>
  </div>
  <span style="font-size:0.8125rem;color:#a0a0a0;font-family:Inter,sans-serif">Crimson knob slid left → dark mode</span>
</div>
</div>
