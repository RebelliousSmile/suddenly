# Charte graphique — Suddenly

**Date** : 2026-04-05 (mise a jour apres audit)
**Outil** : UnoCSS 0.58 + HTMX 1.9 + Alpine.js 3.14
**Build** : Vite 5.4 -> `/static/dist/` via `{% vite_asset %}` template tag

---

## 1. Palette de couleurs

### Couleurs principales

```
PRIMARY (Indigo) — Creativite, fiction, identite
+------+------+------+------+------+------+------+------+------+------+------+
|  50  | 100  | 200  | 300  | 400  | 500  | 600  | 700  | 800  | 900  | 950  |
|eef2ff|e0e7ff|c7d2fe|a5b4fc|818cf8|6366f1|4f46e5|4338ca|3730a3|312e81|1e1b4b|
+------+------+------+------+------+------+------+------+------+------+------+
                                           ^^^^^^ reference (500)
                                                  ^^^^^^ btn-primary (600)

SECONDARY (Emerald) — Liens, connexions, succes
+------+------+------+------+------+------+------+------+------+------+------+
|  50  | 100  | 200  | 300  | 400  | 500  | 600  | 700  | 800  | 900  | 950  |
|ecfdf5|d1fae5|a7f3d0|6ee7b7|34d399|10b981|059669|047857|065f46|064e3b|022c22|
+------+------+------+------+------+------+------+------+------+------+------+

ACCENT (Amber) — Attention, actions, PNJ disponibles
+------+------+------+------+------+------+------+------+------+------+------+
|  50  | 100  | 200  | 300  | 400  | 500  | 600  | 700  | 800  | 900  | 950  |
|fffbeb|fef3c7|fde68a|fcd34d|fbbf24|f59e0b|d97706|b45309|92400e|78350f|451a03|
+------+------+------+------+------+------+------+------+------+------+------+
```

### Couleurs de statut personnage

| Statut | Couleur | Badge UnoCSS | Palette |
|--------|---------|-------------|---------|
| PNJ disponible | vert | `badge-available` | `bg-green-100 text-green-800` |
| Reclame (Claim) | ambre | `badge-claimed` | `bg-amber-100 text-amber-800` |
| Adopte (Adopt) | indigo | `badge-adopted` | `bg-indigo-100 text-indigo-800` |
| Derive (Fork) | violet | `badge-forked` | `bg-violet-100 text-violet-800` |
| PJ actif | bleu | `badge-pc` | `bg-blue-100 text-blue-800` |

### Couleurs systeme (CSS custom properties)

| Role | Valeur light | Valeur dark (prep) | Variable CSS |
|------|-------------|-------------------|--------------|
| Background | `#fafafa` | `#111827` | `--color-bg` |
| Surface | `#ffffff` | `#1f2937` | `--color-surface` |
| Texte principal | `#1f2937` | `#f9fafb` | `--color-text` |
| Texte secondaire | `#4b5563` | `#9ca3af` | `--color-text-secondary` |
| Bordures | `#e5e7eb` | `#374151` | `--color-border` |
| Primary | `#4f46e5` | — | `--color-primary` |
| Secondary | `#10b981` | — | `--color-secondary` |
| Accent | `#f59e0b` | — | `--color-accent` |

### Couleurs de feedback

| Type | Fond | Texte | Bordure |
|------|------|-------|---------|
| Success | `#d1fae5` (green-50) | `#065f46` (green-800) | `green-200` |
| Error | `#fee2e2` (red-50) | `#991b1b` (red-800) | `red-200` |
| Warning | `#fef3c7` (amber-50) | `#92400e` (amber-800) | `amber-200` |
| Info | `#dbeafe` (blue-50) | `#1e40af` (blue-800) | `blue-200` |

### Regle de contraste WCAG AA

- Texte informatif : minimum `text-gray-500` (#6b7280) sur fond blanc — ratio 4.6:1
- Texte secondaire : `text-gray-600` (#4b5563) — ratio 7.0:1 (utilise pour `form-help`)
- **Interdit** : `text-gray-400` pour du texte porteur de sens (ratio 3.0:1, echec WCAG)
- Accepte : `text-gray-400` pour separateurs purement decoratifs (tirets, barres)

---

## 2. Typographie

### Familles

```
SANS-SERIF (corps, UI)
  Inter, system-ui, -apple-system, sans-serif
  Chargement : Google Fonts CDN (preconnect)
  Usage : tout le texte d'interface

SERIF (citations, accents narratifs)
  Lora, Georgia, serif
  Usage : blockquotes dans quote_card, contenu narratif

MONOSPACE (editeur, code)
  JetBrains Mono, Fira Code, monospace
  Usage : textarea de l'editeur de CR
```

### Echelle

| Classe | Taille | Line-height | Usage |
|--------|--------|-------------|-------|
| `text-xs` | 0.75rem | 1rem | metadonnees, timestamps |
| `text-sm` | 0.875rem | 1.25rem | labels, texte secondaire |
| `text-base` | 1rem | 1.5rem | corps de texte |
| `text-lg` | 1.125rem | 1.75rem | citations (serif italic) |
| `text-xl` | 1.25rem | 1.75rem | titres de section |
| `text-2xl` | 1.5rem | 2rem | titres de page |
| `text-4xl` | 2.25rem | 2.5rem | hero |

### Graisses

| Classe | Poids | Usage |
|--------|-------|-------|
| `font-normal` | 400 | corps de texte |
| `font-medium` | 500 | boutons, labels |
| `font-semibold` | 600 | titres de section (`text-heading`) |
| `font-bold` | 700 | logo, hero |

---

## 3. Espacement et layout

### Container

```
container-app = max-w-7xl mx-auto px-4 sm:px-6 lg:px-8

  mobile (<640px)  : 16px lateral
  tablet (640-1024): 24px lateral
  desktop (>1024)  : 32px lateral
  max-width        : 1280px
```

### Grille responsive

```
Cards (3 col)   : grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4
Cards (4 col)   : grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3
Sidebar+content : flex flex-col md:flex-row gap-6 (sidebar w-56)
```

### Tokens d'espacement

| Token | Valeur | Usage |
|-------|--------|-------|
| `gap-1` | 0.25rem | entre badges inline |
| `gap-2` | 0.5rem | entre elements d'une ligne |
| `gap-3` | 0.75rem | entre cards compactes |
| `gap-4` | 1rem | entre cards standard |
| `gap-6` | 1.5rem | entre sections majeures |
| `gap-8` | 2rem | entre blocs de page |

---

## 4. Coins, ombres, z-index

### Border radius

| Token | Valeur | Usage |
|-------|--------|-------|
| `rounded-button` | 0.5rem | boutons, inputs |
| `rounded-card` | 0.75rem | cards, modals, dropdowns |
| `rounded-badge` | 9999px | badges (pill) |
| `rounded-full` | 50% | avatars |

### Ombres

| Token | Usage |
|-------|-------|
| `shadow-card` | cards au repos |
| `shadow-card-hover` | cards au hover |
| `shadow-dropdown` | menus flottants, modals |

### Z-index (echelle semantique)

| Token | Valeur | Usage |
|-------|--------|-------|
| `z-dropdown` | 10 | menus contextuels, suggestions |
| `z-sticky` | 20 | header sticky |
| `z-overlay` | 30 | backdrop modal |
| `z-modal` | 40 | contenu modal |
| `z-toast` | 50 | toasts, loading bar |

---

## 5. Animation

### Durees

| Token | Valeur | Usage |
|-------|--------|-------|
| `duration-fast` | 100ms | dropdown enter/leave |
| `duration-normal` | 200ms | modal leave, transitions standard |
| `duration-slow` | 300ms | modal enter |

### Easing

| Token | Courbe | Usage |
|-------|--------|-------|
| `ease-in` | `cubic-bezier(0.4, 0, 1, 1)` | fermeture |
| `ease-out` | `cubic-bezier(0, 0, 0.2, 1)` | ouverture |
| `ease-in-out` | `cubic-bezier(0.4, 0, 0.2, 1)` | general |

### Reduced motion

`@media (prefers-reduced-motion: reduce)` desactive toutes les animations
(defini dans `static/css/style.css`).

---

## 6. Composants UnoCSS (shortcuts)

### Boutons

| Shortcut | Apparence | Usage |
|----------|-----------|-------|
| `btn-primary` | Indigo 600, texte blanc | action principale |
| `btn-secondary` | Fond blanc, bordure grise | action secondaire |
| `btn-ghost` | Transparent, texte gris | action tertiaire |
| `btn-danger` | Rouge 600, texte blanc | action destructive |
| `btn-sm` | Taille reduite (modificateur) | actions inline |
| `btn-lg` | Taille agrandie (modificateur) | hero CTA |

### Cards

| Shortcut | Description |
|----------|-------------|
| `card` | bg-white, border, rounded-card, shadow |
| `card-hover` | card + shadow au hover |
| `card-body` | padding responsive |
| `card-header` | padding + border-bottom |
| `card-footer` | padding + bg-gray-50 + border-top |

### Badges

| Shortcut | Couleur | Icone associee |
|----------|---------|----------------|
| `badge-available` | vert | `i-lucide-circle-dot` |
| `badge-claimed` | ambre | `i-lucide-git-merge` |
| `badge-adopted` | indigo | `i-lucide-user-check` |
| `badge-forked` | violet | `i-lucide-git-branch` |
| `badge-pc` | bleu | `i-lucide-star` |
| `badge-primary` | indigo | generique |
| `badge-secondary` | emerald | generique |
| `badge-accent` | ambre | generique |
| `badge-gray` | gris | brouillon, prive |

### Avatars

| Shortcut | Taille | Usage |
|----------|--------|-------|
| `avatar-sm` | 32px | listes, metadata |
| `avatar-md` | 40px | en-tetes de cards |
| `avatar-lg` | 48px | cards personnage |
| `avatar-xl` | 64px | detail, profil |
| `avatar-placeholder` | — | fond primary-100, icone |

### Formulaires

| Shortcut | Description |
|----------|-------------|
| `form-input` | input standard avec bordure, focus ring |
| `form-input-error` | input en etat d'erreur (bordure rouge) |
| `form-label` | label standard |
| `form-help` | texte d'aide (`text-gray-600`) |
| `form-error` | message d'erreur (`text-red-600`) |
| `form-dropzone` | zone drag-and-drop avec bordure tiretee |
| `form-dropzone-link` | lien "Televerser" dans la dropzone |

### Menus

| Shortcut | Description |
|----------|-------------|
| `dropdown-menu` | menu contextuel (bg-white, shadow-dropdown, border, z-dropdown) |

### Instance badge (portee federation)

Badge discret indiquant l'instance d'origine du contenu.
Visible sur : feed Fediverse, cards distantes, profils distants.
Pas affiche si le contenu est local (implicite).

```
(globe) suddenly.games        <- format inline
text-xs text-gray-500 flex items-center gap-1 + i-lucide-globe
```

### Liens et texte

| Shortcut | Description |
|----------|-------------|
| `link` | lien primary avec underline au hover |
| `link-muted` | lien gris discret |
| `text-muted` | texte gris 500 |
| `text-heading` | texte gray-900 font-semibold |
| `prose-report` | prose Markdown pour les CRs |

---

## 7. Iconographie

### Bibliotheque : Lucide (via @iconify-json/lucide)

Format UnoCSS : `i-lucide-{nom}`. Taille par defaut : `1.2em` (scale dans config).

| Categorie | Icones |
|-----------|--------|
| Navigation | `home`, `compass`, `book-open`, `users`, `bell`, `menu`, `search`, `user`, `settings`, `log-out` |
| Actions personnage | `git-merge` (claim), `heart` (adopt), `git-branch` (fork), `sparkles` (PNJ), `star` (PJ) |
| Actions generiques | `plus`, `edit`, `trash`, `check`, `x`, `link`, `share`, `flag`, `copy`, `send`, `save` |
| Etats | `clock`, `lock`, `globe`, `alert-triangle`, `info`, `check-circle`, `x-circle`, `shield-x`, `search-x` |
| Autosave | `cloud` (saved), `cloud-off` (unsaved), `loader-2` (saving) |
| Social | `message-circle`, `rss`, `user-plus`, `user-check`, `chevron-down`, `chevron-right` |
| Fichiers | `upload`, `download`, `external-link` |
| Externe | `i-simple-icons-mastodon`, `i-simple-icons-github` |

---

## 8. Composants Alpine.js

| Composant | Data | Methodes | Usage |
|-----------|------|----------|-------|
| `dropdown` | `open` | `toggle()`, `close()` | menus contextuels |
| `modal` | `open` | `show()`, `hide()` | modals (gere body scroll) |
| `notifications` | `items[]` | `add({message,type,duration})`, `remove(id)` | toasts |
| `mentionInput` | `content`, `suggestions[]` | `onInput()`, `search()`, `selectSuggestion()`, `onKeydown()` | editeur CR @mentions |
| `tabs` | `activeTab` | `isActive(tab)`, `select(tab)` | onglets |
| `characterStatus` | `status` | `statusLabel`, `statusClass` | badge dynamique |
| `passwordStrength` | `strength`, `label` | `evaluate(password)` | barre de force mot de passe |
| `autosave` | `status` | `markDirty()`, `save()` | sauvegarde auto editeur |
| `presence` | `participants[]` | `poll()`, `heartbeat()` | indicateur SharedSequence |

---

## 9. Patterns d'interaction

### HTMX

| Pattern | Attributs | Usage |
|---------|-----------|-------|
| Recherche live | `hx-get hx-trigger="keyup changed delay:300ms" hx-target="#results"` | liste personnages, recherche federee |
| Pagination infinie | `hx-get="?page=N" hx-trigger="revealed" hx-swap="afterend"` | feed, listes |
| Formulaire inline | `hx-post hx-target="#container" hx-swap="innerHTML"` | ajout citation |
| Toggle | `hx-post hx-target="this" hx-swap="outerHTML"` | bouton follow |
| Loading | classe `.htmx-indicator` + CSS dans `htmx-indicator.css` | barre progress |

### CSRF

Methode unique : `htmx:configRequest` dans `main.js` lit le cookie `csrftoken`
ou le champ `csrfmiddlewaretoken`. Pas de `hx-headers` sur body.

---

## 10. Responsive

### Breakpoints

| Token | Largeur | Usage |
|-------|---------|-------|
| `sm` | 640px | tablets portrait |
| `md` | 768px | tablets landscape |
| `lg` | 1024px | desktop |
| `xl` | 1280px | wide desktop |

### Regles

- **Mobile first** : tout le CSS est mobile par defaut
- Header : hamburger -> nav horizontale a `md`
- Grilles : 1 col -> 2 col a `sm` -> 3-4 col a `lg`
- Settings sidebar : empile -> cote a cote a `md`
- Fiche perso : empile -> sidebar+content a `lg`

---

## 11. Build et integration Django

### Vite build

```
Entree  : frontend/src/main.js
Sortie  : static/dist/ (js/main.js, css/main.css)
Manifest: static/dist/.vite/manifest.json
```

### Template tag `{% vite_asset %}`

```django
{% load vite %}
{% vite_css %}                     {# CSS avec hash du manifest #}
{% vite_asset "src/main.js" %}     {# JS avec hash du manifest #}
```

Lit le manifest Vite pour resoudre les noms hashes.
Fallback sur chemins predictibles si pas de manifest (dev).
Cache le manifest en memoire en production.

### Safelist

Toute classe generee dynamiquement en Python (template tags, variables
de contexte) **doit** etre ajoutee dans la safelist de `uno.config.js`.
Le scanner UnoCSS ne detecte que les classes presentes litteralement
dans les fichiers HTML/PY.

---

## 12. Inventaire des composants template

### 16 composants (`templates/components/`)

| Composant | Fichier | Cree | Props principales |
|-----------|---------|------|-------------------|
| Character card | `character_card.html` | existant | `character`, `show_actions` |
| Report card | `report_card.html` | existant | `report` |
| Game card | `game_card.html` | existant | `game`, `compact` |
| Quote card | `quote_card.html` | existant | `quote` |
| Modal | `modal.html` | existant | `title`, blocks `modal_body`/`modal_footer` |
| Report editor | `report_editor.html` | existant | `game`, `report` |
| Form fields | `form_fields.html` | existant | macros `input`/`textarea`/`select`/`checkbox`/`file_upload` |
| Follow button | `follow_button.html` | nouveau | `target`, `target_type`, `is_following` |
| Link request card | `link_request_card.html` | nouveau | `request`, `perspective` |
| Notification item | `notification_item.html` | nouveau | `notification` |
| Feed item | `feed_item.html` | nouveau | `report` |
| NPC highlight | `npc_highlight.html` | nouveau | `character` |
| Empty state | `empty_state.html` | nouveau | `icon`, `title`, `description`, `cta_label`, `cta_url` |
| Status banner | `status_banner.html` | nouveau | `type`, `icon`, `message`, `action_label`, `dismiss` |
| Presence indicator | `presence_indicator.html` | nouveau | `participants` |
| Password strength | `password_strength.html` | nouveau | `field_id` |
