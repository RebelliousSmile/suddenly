# Dark/Light Mode — Part 1: CSS Variables + Palette

## Feature

- **Summary**: Migrer les couleurs de valeurs hex statiques vers des CSS custom properties. Ajouter violet comme accent principal. Aucun changement de template requis.
- **Stack**: `UnoCSS 0.62`, `Vite 5.4`
- **Branch name**: `feat/dark-light-mode`
- **Parent Plan**: `2026_04_28-dark-light-mode-master.md`
- **Sequence**: `1 of 3`
- Confidence: 9/10
- Time to implement: 45min

## Existing files

- @frontend/uno.config.js
- @frontend/src/base.css

### New files to create

- none

## User Journey

```mermaid
flowchart TD
  A[base.css — CSS variables déclarées] --> B[uno.config.js — couleurs pointent vers var()]
  B --> C[Shortcuts btn-primary / label-overline → violet]
  C --> D[pnpm run build — validation]
  D --> E[Tokens prêts pour Part 2]
```

## Implementation phases

### Phase 1 — base.css : déclaration des CSS custom properties

> Déclarer toutes les variables sémantiques en light (`:root`) et dark (`[data-theme="dark"]`).

1. Remplacer le contenu de `base.css` par :
   - `:root` block avec les valeurs light (parchemin chaud)
   - `[data-theme="dark"]` block avec les valeurs dark (néon dans la nuit)
   - `body` avec `background: var(--body-bg)` et `color: var(--c-primary)`
   - `a { text-decoration: none }`
   - Variables à déclarer : `--c-bg`, `--c-surface`, `--c-card`, `--c-card-dark`, `--c-border`, `--c-primary`, `--c-secondary`, `--c-muted`, `--shadow-card`, `--shadow-card-hover`, `--body-bg`
   - Valeurs : voir master plan section "Design tokens"

### Phase 2 — uno.config.js : couleurs → CSS variables

> Remplacer les hex statiques par des références aux CSS variables. Ajouter violet comme accent principal.

1. Mettre à jour le bloc `colors` :
   - `background: 'var(--c-bg)'`
   - `surface: 'var(--c-surface)'`
   - `card: { DEFAULT: 'var(--c-card)', dark: 'var(--c-card-dark)' }`
   - `border: 'var(--c-border)'`
   - `primary: 'var(--c-primary)'`
   - `secondary: 'var(--c-secondary)'`
   - `muted: 'var(--c-muted)'`
   - Ajouter : `violet: { DEFAULT: '#7c3aed', hover: '#6d28d9' }`
   - Conserver : `crimson`, `success`, `warning`, `error`, `info` en hex (identiques dark/light)

2. Mettre à jour les `boxShadow` tokens :
   - `card: 'var(--shadow-card)'`
   - `card-hover: 'var(--shadow-card-hover)'`
   - Conserver : `btn: '0 4px 20px rgba(124,58,237,0.35)'` (violet glow, plus crimson)

3. Mettre à jour les shortcuts :
   - `btn-primary` → remplacer `bg-crimson` par `bg-violet`, `hover:bg-crimson-hover` par `hover:bg-violet-hover`, `hover:shadow-btn` inchangé
   - `btn-secondary` → `hover:border-violet hover:text-violet` (était crimson)
   - `label-overline` → `text-violet` (était `text-crimson`)
   - `link` → `text-violet hover:text-violet-hover` (était crimson)
   - Conserver `btn-danger` sur crimson (sémantique correcte)
   - `dropdown-menu` → `bg-surface border-border` (déjà OK, CSS variables résoudront)
   - `form-dropzone-link` → `text-violet` (était crimson)
   - `avatar` → `bg-surface` (CSS variable, OK)

4. Mettre à jour le safelist : ajouter `bg-violet/10`, `text-violet`, `border-violet/30` si utilisés dynamiquement

### Phase 3 — Validation build

1. `cd frontend && pnpm run build` — doit compiler sans erreur
2. Vérifier que `var(--c-bg)` apparaît dans le CSS généré
3. Vérifier que `#7c3aed` apparaît pour violet

## Validation flow

1. `pnpm run build` sans erreur
2. Inspecter le CSS généré : classes `bg-surface`, `text-primary` référencent des `var(--c-*)`
3. `python manage.py runserver` — page visible (en light mode par défaut, toggle pas encore là)
