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

---

## Images & Avatars

Avatars follow the `avatar-*` size scale. Always provide a `avatar-placeholder` fallback when no image is available.

| Class | Size | Usage |
|-------|------|-------|
| `avatar-sm` | 32 × 32 px | Stacked groups, inline meta |
| `avatar-md` | 40 × 40 px | List items, compact cards |
| `avatar-lg` | 48 × 48 px | Card headers |
| `avatar-xl` | 64 × 64 px | Profile page header |
| `avatar-placeholder` | any size | Fallback — icon on `bg-surface` |

### Avatar sizes

Same image at each scale. The `border-radius: 9999px` and `object-fit: cover` are applied by the `avatar` base class.

<div class="sd-light">
<span class="sd-label">Light mode — with image</span>
<div class="sd-row" style="align-items:flex-end;gap:1.5rem">
  <div style="display:flex;flex-direction:column;align-items:center;gap:0.4rem">
    <img class="sd-avatar sd-avatar-sm" src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=32&h=32&fit=crop&auto=format&q=80" alt="Seraphina">
    <span class="sd-swatch-name">sm · 32px</span>
  </div>
  <div style="display:flex;flex-direction:column;align-items:center;gap:0.4rem">
    <img class="sd-avatar sd-avatar-md" src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=40&h=40&fit=crop&auto=format&q=80" alt="Seraphina">
    <span class="sd-swatch-name">md · 40px</span>
  </div>
  <div style="display:flex;flex-direction:column;align-items:center;gap:0.4rem">
    <img class="sd-avatar sd-avatar-lg" src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=48&h=48&fit=crop&auto=format&q=80" alt="Seraphina">
    <span class="sd-swatch-name">lg · 48px</span>
  </div>
  <div style="display:flex;flex-direction:column;align-items:center;gap:0.4rem">
    <img class="sd-avatar sd-avatar-xl" src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=64&h=64&fit=crop&auto=format&q=80" alt="Seraphina">
    <span class="sd-swatch-name">xl · 64px</span>
  </div>
  <div style="width:1px;height:64px;background:#d4cfe8;margin:0 0.5rem"></div>
  <div style="display:flex;flex-direction:column;align-items:center;gap:0.4rem">
    <span class="sd-avatar sd-avatar-xl sd-avatar-placeholder"><span style="font-size:1.4rem">✦</span></span>
    <span class="sd-swatch-name">placeholder</span>
  </div>
</div>
</div>

<div class="sd-dark">
<span class="sd-label">Dark mode — with image</span>
<div class="sd-row" style="align-items:flex-end;gap:1.5rem">
  <div style="display:flex;flex-direction:column;align-items:center;gap:0.4rem">
    <img class="sd-avatar sd-avatar-sm" src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=32&h=32&fit=crop&auto=format&q=80" alt="Seraphina">
    <span class="sd-swatch-name" style="color:#606060">sm · 32px</span>
  </div>
  <div style="display:flex;flex-direction:column;align-items:center;gap:0.4rem">
    <img class="sd-avatar sd-avatar-md" src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=40&h=40&fit=crop&auto=format&q=80" alt="Seraphina">
    <span class="sd-swatch-name" style="color:#606060">md · 40px</span>
  </div>
  <div style="display:flex;flex-direction:column;align-items:center;gap:0.4rem">
    <img class="sd-avatar sd-avatar-lg" src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=48&h=48&fit=crop&auto=format&q=80" alt="Seraphina">
    <span class="sd-swatch-name" style="color:#606060">lg · 48px</span>
  </div>
  <div style="display:flex;flex-direction:column;align-items:center;gap:0.4rem">
    <img class="sd-avatar sd-avatar-xl" src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=64&h=64&fit=crop&auto=format&q=80" alt="Seraphina">
    <span class="sd-swatch-name" style="color:#606060">xl · 64px</span>
  </div>
  <div style="width:1px;height:64px;background:#2a2a2a;margin:0 0.5rem"></div>
  <div style="display:flex;flex-direction:column;align-items:center;gap:0.4rem">
    <span class="sd-avatar sd-avatar-xl sd-avatar-placeholder" style="background:#1a1a1a;border-color:#2a2a2a;color:#606060"><span style="font-size:1.4rem">✦</span></span>
    <span class="sd-swatch-name" style="color:#606060">placeholder</span>
  </div>
</div>
</div>

### Stacked avatar group

Used in game cards to show recent characters (`-space-x-2`, `ring-2 ring-card`). Overflow beyond 5 shown as `+N` chip.

<div class="sd-light">
<span class="sd-label">Light mode</span>
<div class="sd-stack">
  <img class="sd-avatar sd-avatar-sm" style="z-index:5;outline:2px solid #ffffff" src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=32&h=32&fit=crop&auto=format&q=80" alt="Seraphina">
  <img class="sd-avatar sd-avatar-sm" style="z-index:4;outline:2px solid #ffffff" src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=32&h=32&fit=crop&auto=format&q=80" alt="Kael">
  <img class="sd-avatar sd-avatar-sm" style="z-index:3;outline:2px solid #ffffff" src="https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=32&h=32&fit=crop&auto=format&q=80" alt="Lady Morrow">
  <img class="sd-avatar sd-avatar-sm" style="z-index:2;outline:2px solid #ffffff" src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=32&h=32&fit=crop&auto=format&q=80" alt="Draven">
  <img class="sd-avatar sd-avatar-sm" style="z-index:1;outline:2px solid #ffffff" src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=32&h=32&fit=crop&auto=format&q=80" alt="Vex">
  <span class="sd-avatar sd-avatar-sm sd-stack-overflow">+3</span>
</div>
</div>

<div class="sd-dark">
<span class="sd-label">Dark mode</span>
<div class="sd-stack">
  <img class="sd-avatar sd-avatar-sm" style="z-index:5;outline:2px solid #0a0a0a" src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=32&h=32&fit=crop&auto=format&q=80" alt="Seraphina">
  <img class="sd-avatar sd-avatar-sm" style="z-index:4;outline:2px solid #0a0a0a" src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=32&h=32&fit=crop&auto=format&q=80" alt="Kael">
  <img class="sd-avatar sd-avatar-sm" style="z-index:3;outline:2px solid #0a0a0a" src="https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=32&h=32&fit=crop&auto=format&q=80" alt="Lady Morrow">
  <img class="sd-avatar sd-avatar-sm" style="z-index:2;outline:2px solid #0a0a0a" src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=32&h=32&fit=crop&auto=format&q=80" alt="Draven">
  <img class="sd-avatar sd-avatar-sm" style="z-index:1;outline:2px solid #0a0a0a" src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=32&h=32&fit=crop&auto=format&q=80" alt="Vex">
  <span class="sd-avatar sd-avatar-sm sd-stack-overflow" style="background:#222222;border-color:#2a2a2a;color:#a0a0a0;outline:2px solid #0a0a0a">+3</span>
</div>
</div>

---

## Lists & Grids

Three layout patterns are used across the app depending on context.

| Pattern | Classes | Usage |
|---------|---------|-------|
| Card grid | `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4` | Characters list, games list |
| Compact grid | `grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3` | Profile characters |
| Vertical stack | `space-y-3` | Profile games, feed, notifications |
| Empty state | `components/empty_state.html` | Any empty list |

### Card grid — 3 columns

<div class="sd-light">
<span class="sd-label">Light mode — characters / games list</span>
<div class="sd-grid-3">
  <div class="sd-card">
    <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem">
      <img class="sd-avatar sd-avatar-md" src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=40&h=40&fit=crop&auto=format&q=80" alt="Seraphina Voss">
      <div>
        <p class="sd-card-title" style="font-size:0.9375rem">Seraphina Voss</p>
        <span class="sd-badge sd-badge-adopted">Adopted</span>
      </div>
    </div>
    <p class="sd-card-body">Former archivist, now rogue. Introduced in session 3.</p>
  </div>
  <div class="sd-card">
    <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem">
      <img class="sd-avatar sd-avatar-md" src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=40&h=40&fit=crop&auto=format&q=80" alt="Brother Kael">
      <div>
        <p class="sd-card-title" style="font-size:0.9375rem">Brother Kael</p>
        <span class="sd-badge sd-badge-available">Available</span>
      </div>
    </div>
    <p class="sd-card-body">Wandering healer. Has not been claimed yet.</p>
  </div>
  <div class="sd-card">
    <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem">
      <img class="sd-avatar sd-avatar-md" src="https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=40&h=40&fit=crop&auto=format&q=80" alt="Lady Morrow">
      <div>
        <p class="sd-card-title" style="font-size:0.9375rem">Lady Morrow</p>
        <span class="sd-badge sd-badge-pc">PC</span>
      </div>
    </div>
    <p class="sd-card-body">Player character — originally an NPC from <a class="sd-link" href="#">Iron Season</a>.</p>
  </div>
</div>
</div>

<div class="sd-dark">
<span class="sd-label">Dark mode</span>
<div class="sd-grid-3">
  <div class="sd-card">
    <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem">
      <img class="sd-avatar sd-avatar-md" src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=40&h=40&fit=crop&auto=format&q=80" alt="Seraphina Voss">
      <div>
        <p class="sd-card-title" style="font-size:0.9375rem">Seraphina Voss</p>
        <span class="sd-badge sd-badge-adopted">Adopted</span>
      </div>
    </div>
    <p class="sd-card-body">Former archivist, now rogue. Introduced in session 3.</p>
  </div>
  <div class="sd-card">
    <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem">
      <img class="sd-avatar sd-avatar-md" src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=40&h=40&fit=crop&auto=format&q=80" alt="Brother Kael">
      <div>
        <p class="sd-card-title" style="font-size:0.9375rem">Brother Kael</p>
        <span class="sd-badge sd-badge-available">Available</span>
      </div>
    </div>
    <p class="sd-card-body">Wandering healer. Has not been claimed yet.</p>
  </div>
  <div class="sd-card">
    <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem">
      <img class="sd-avatar sd-avatar-md" src="https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=40&h=40&fit=crop&auto=format&q=80" alt="Lady Morrow">
      <div>
        <p class="sd-card-title" style="font-size:0.9375rem">Lady Morrow</p>
        <span class="sd-badge sd-badge-pc">PC</span>
      </div>
    </div>
    <p class="sd-card-body">Player character — originally an NPC from <a class="sd-link" href="#">Iron Season</a>.</p>
  </div>
</div>
</div>

### Compact grid — 4 columns

Used on profile pages to show a user's characters without full card detail.

<div class="sd-light">
<span class="sd-label">Light mode — profile characters</span>
<div class="sd-grid-4">
  <div class="sd-card" style="text-align:center;padding:0.875rem">
    <p class="sd-card-title" style="font-size:0.875rem">Seraphina</p>
    <span class="sd-badge sd-badge-adopted" style="font-size:0.65rem">Adopted</span>
  </div>
  <div class="sd-card" style="text-align:center;padding:0.875rem">
    <p class="sd-card-title" style="font-size:0.875rem">Kael</p>
    <span class="sd-badge sd-badge-available" style="font-size:0.65rem">Available</span>
  </div>
  <div class="sd-card" style="text-align:center;padding:0.875rem">
    <p class="sd-card-title" style="font-size:0.875rem">Lady Morrow</p>
    <span class="sd-badge sd-badge-pc" style="font-size:0.65rem">PC</span>
  </div>
  <div class="sd-card" style="text-align:center;padding:0.875rem">
    <p class="sd-card-title" style="font-size:0.875rem">Draven</p>
    <span class="sd-badge sd-badge-forked" style="font-size:0.65rem">Forked</span>
  </div>
</div>
</div>

<div class="sd-dark">
<span class="sd-label">Dark mode</span>
<div class="sd-grid-4">
  <div class="sd-card" style="text-align:center;padding:0.875rem">
    <p class="sd-card-title" style="font-size:0.875rem">Seraphina</p>
    <span class="sd-badge sd-badge-adopted" style="font-size:0.65rem">Adopted</span>
  </div>
  <div class="sd-card" style="text-align:center;padding:0.875rem">
    <p class="sd-card-title" style="font-size:0.875rem">Kael</p>
    <span class="sd-badge sd-badge-available" style="font-size:0.65rem">Available</span>
  </div>
  <div class="sd-card" style="text-align:center;padding:0.875rem">
    <p class="sd-card-title" style="font-size:0.875rem">Lady Morrow</p>
    <span class="sd-badge sd-badge-pc" style="font-size:0.65rem">PC</span>
  </div>
  <div class="sd-card" style="text-align:center;padding:0.875rem">
    <p class="sd-card-title" style="font-size:0.875rem">Draven</p>
    <span class="sd-badge sd-badge-forked" style="font-size:0.65rem">Forked</span>
  </div>
</div>
</div>

### Vertical stack

Used for games on profile pages, notifications, feed items. Items breathe with `space-y-3`.

<div class="sd-light">
<span class="sd-label">Light mode — profile games / feed</span>
<div class="sd-stack-y">
  <div class="sd-card">
    <p class="sd-card-title">City of Mist — Season 2</p>
    <p class="sd-card-body">City of Mist</p>
  </div>
  <div class="sd-card">
    <p class="sd-card-title">Iron Season</p>
    <p class="sd-card-body">Ironsworn</p>
  </div>
  <div class="sd-card">
    <p class="sd-card-title">The Long Road</p>
    <p class="sd-card-body">Blades in the Dark</p>
  </div>
</div>
</div>

<div class="sd-dark">
<span class="sd-label">Dark mode</span>
<div class="sd-stack-y">
  <div class="sd-card">
    <p class="sd-card-title">City of Mist — Season 2</p>
    <p class="sd-card-body">City of Mist</p>
  </div>
  <div class="sd-card">
    <p class="sd-card-title">Iron Season</p>
    <p class="sd-card-body">Ironsworn</p>
  </div>
  <div class="sd-card">
    <p class="sd-card-title">The Long Road</p>
    <p class="sd-card-body">Blades in the Dark</p>
  </div>
</div>
</div>

### Empty state

Used whenever a list has no items. Always includes icon + title, optionally description + CTA.

<div class="sd-light">
<span class="sd-label">Light mode — with CTA</span>
<div class="sd-empty-state">
  <span class="sd-empty-icon">📖</span>
  <p class="sd-empty-title">No games yet</p>
  <p class="sd-empty-desc">Create your first game to start publishing session reports.</p>
  <button class="sd-btn sd-btn-primary sd-btn-sm">New game</button>
</div>
</div>

<div class="sd-dark">
<span class="sd-label">Dark mode — search empty</span>
<div class="sd-empty-state">
  <span class="sd-empty-icon" style="filter:grayscale(0.3)">🔍</span>
  <p class="sd-empty-title" style="color:#f0f0f0">No characters found</p>
  <p class="sd-empty-desc" style="color:#606060">Try different search terms or filters.</p>
</div>
</div>

---

## Forms

Forms are wrapped in `card card-body space-y-4`. Each field follows the same structure: label → input → help/error.

| Class | Element | Usage |
|-------|---------|-------|
| `form-label` | `<label>` | Field label — Inter 500, `text-secondary` |
| `form-input` | `<input>`, `<textarea>`, `<select>` | Base input style |
| `form-input-error` | same elements | Error state — crimson border + ring |
| `form-help` | `<p>` | Helper text below field |
| `form-error` | `<p>` | Validation error below field |
| `form-dropzone` | `<div>` | File upload zone |
| `form-dropzone-link` | `<label>` | Clickable part of dropzone |

Optional fields carry `(optional)` in muted text next to the label.

### Text input — states

<div class="sd-light">
<span class="sd-label">Light mode</span>
<div style="display:flex;flex-direction:column;gap:1.25rem">
  <div>
    <label class="sd-form-label">Title <span style="color:#e03558">*</span></label>
    <input class="sd-input" type="text" placeholder="e.g. City of Mist — Season 2" style="max-width:100%">
  </div>
  <div>
    <label class="sd-form-label">Game system <span style="color:#8a8aaa;font-weight:400">(optional)</span></label>
    <input class="sd-input" type="text" value="Ironsworn" style="max-width:100%">
    <p class="sd-form-help">The rule system used for this campaign.</p>
  </div>
  <div>
    <label class="sd-form-label">Start date <span style="color:#8a8aaa;font-weight:400">(optional)</span></label>
    <input class="sd-input sd-input-error" type="date" style="max-width:100%">
    <p class="sd-form-error">Invalid date format.</p>
  </div>
</div>
</div>

<div class="sd-dark">
<span class="sd-label">Dark mode</span>
<div style="display:flex;flex-direction:column;gap:1.25rem">
  <div>
    <label class="sd-form-label" style="color:#a0a0a0">Title <span style="color:#e03558">*</span></label>
    <input class="sd-input" type="text" placeholder="e.g. City of Mist — Season 2" style="max-width:100%">
  </div>
  <div>
    <label class="sd-form-label" style="color:#a0a0a0">Game system <span style="color:#606060;font-weight:400">(optional)</span></label>
    <input class="sd-input" type="text" value="Ironsworn" style="max-width:100%">
    <p class="sd-form-help" style="color:#606060">The rule system used for this campaign.</p>
  </div>
  <div>
    <label class="sd-form-label" style="color:#a0a0a0">Start date <span style="color:#606060;font-weight:400">(optional)</span></label>
    <input class="sd-input sd-input-error" type="date" style="max-width:100%">
    <p class="sd-form-error">Invalid date format.</p>
  </div>
</div>
</div>

### Textarea

<div class="sd-light">
<span class="sd-label">Light mode</span>
<div>
  <label class="sd-form-label">Description <span style="color:#8a8aaa;font-weight:400">(optional)</span></label>
  <textarea class="sd-input" rows="3" placeholder="Describe your campaign..." style="max-width:100%;resize:vertical"></textarea>
</div>
</div>

<div class="sd-dark">
<span class="sd-label">Dark mode</span>
<div>
  <label class="sd-form-label" style="color:#a0a0a0">Description <span style="color:#606060;font-weight:400">(optional)</span></label>
  <textarea class="sd-input" rows="3" placeholder="Describe your campaign..." style="max-width:100%;resize:vertical"></textarea>
</div>
</div>

### Checkbox

<div class="sd-light">
<span class="sd-label">Light mode</span>
<div style="display:flex;align-items:flex-start;gap:0.75rem">
  <input type="checkbox" checked class="sd-checkbox">
  <div>
    <label class="sd-form-label" style="margin-bottom:0">Public game (visible and followable)</label>
    <p class="sd-form-help">Anyone can follow this game via ActivityPub.</p>
  </div>
</div>
</div>

<div class="sd-dark">
<span class="sd-label">Dark mode</span>
<div style="display:flex;align-items:flex-start;gap:0.75rem">
  <input type="checkbox" checked class="sd-checkbox">
  <div>
    <label class="sd-form-label" style="margin-bottom:0;color:#a0a0a0">Public game (visible and followable)</label>
    <p class="sd-form-help" style="color:#606060">Anyone can follow this game via ActivityPub.</p>
  </div>
</div>
</div>

### File upload dropzone

<div class="sd-light">
<span class="sd-label">Light mode</span>
<div class="sd-dropzone">
  <span style="font-size:2rem;display:block;margin-bottom:0.5rem">⬆</span>
  <p style="font-size:0.875rem;margin:0"><span style="color:#e03558;font-weight:500;cursor:pointer">Upload a file</span> or drag and drop</p>
  <p style="font-size:0.75rem;color:#8a8aaa;margin:0.25rem 0 0">PNG, JPG up to 2 MB</p>
</div>
</div>

<div class="sd-dark">
<span class="sd-label">Dark mode</span>
<div class="sd-dropzone" style="background:#1a1a1a;border-color:#2a2a2a">
  <span style="font-size:2rem;display:block;margin-bottom:0.5rem;filter:grayscale(0.5)">⬆</span>
  <p style="font-size:0.875rem;margin:0;color:#a0a0a0"><span style="color:#e03558;font-weight:500;cursor:pointer">Upload a file</span> or drag and drop</p>
  <p style="font-size:0.75rem;color:#606060;margin:0.25rem 0 0">PNG, JPG up to 2 MB</p>
</div>
</div>

### Full form example

<div class="sd-light">
<span class="sd-label">Light mode — game creation form</span>
<div class="sd-card">
<div style="display:flex;flex-direction:column;gap:1rem">
  <div>
    <label class="sd-form-label">Title <span style="color:#e03558">*</span></label>
    <input class="sd-input" type="text" placeholder="e.g. City of Mist — Season 2" style="max-width:100%">
  </div>
  <div>
    <label class="sd-form-label">Game system <span style="color:#8a8aaa;font-weight:400">(optional)</span></label>
    <input class="sd-input" type="text" placeholder="e.g. D&D 5e, Ironsworn" style="max-width:100%">
  </div>
  <div>
    <label class="sd-form-label">Description <span style="color:#8a8aaa;font-weight:400">(optional)</span></label>
    <textarea class="sd-input" rows="3" placeholder="Describe your campaign..." style="max-width:100%;resize:vertical"></textarea>
  </div>
  <div style="display:flex;align-items:center;gap:0.75rem">
    <input type="checkbox" checked class="sd-checkbox">
    <label class="sd-form-label" style="margin-bottom:0">Public game (visible and followable)</label>
  </div>
  <div style="display:flex;align-items:center;gap:0.75rem;padding-top:1rem;border-top:1px solid #d4cfe8">
    <button class="sd-btn sd-btn-primary">Create a game</button>
    <button class="sd-btn sd-btn-ghost">Cancel</button>
  </div>
</div>
</div>
</div>

<div class="sd-dark">
<span class="sd-label">Dark mode</span>
<div class="sd-card">
<div style="display:flex;flex-direction:column;gap:1rem">
  <div>
    <label class="sd-form-label" style="color:#a0a0a0">Title <span style="color:#e03558">*</span></label>
    <input class="sd-input" type="text" placeholder="e.g. City of Mist — Season 2" style="max-width:100%">
  </div>
  <div>
    <label class="sd-form-label" style="color:#a0a0a0">Game system <span style="color:#606060;font-weight:400">(optional)</span></label>
    <input class="sd-input" type="text" placeholder="e.g. D&D 5e, Ironsworn" style="max-width:100%">
  </div>
  <div>
    <label class="sd-form-label" style="color:#a0a0a0">Description <span style="color:#606060;font-weight:400">(optional)</span></label>
    <textarea class="sd-input" rows="3" placeholder="Describe your campaign..." style="max-width:100%;resize:vertical"></textarea>
  </div>
  <div style="display:flex;align-items:center;gap:0.75rem">
    <input type="checkbox" checked class="sd-checkbox">
    <label class="sd-form-label" style="margin-bottom:0;color:#a0a0a0">Public game (visible and followable)</label>
  </div>
  <div style="display:flex;align-items:center;gap:0.75rem;padding-top:1rem;border-top:1px solid #2a2a2a">
    <button class="sd-btn sd-btn-primary">Create a game</button>
    <button class="sd-btn sd-btn-ghost" style="color:#a0a0a0">Cancel</button>
  </div>
</div>
</div>
</div>

### Error banner

Used at the top of a form when server-side validation fails.

<div class="sd-light">
<span class="sd-label">Light mode</span>
<div class="sd-error-banner">A game with this title already exists.</div>
</div>

<div class="sd-dark">
<span class="sd-label">Dark mode</span>
<div class="sd-error-banner">A game with this title already exists.</div>
</div>
