// GENERATED FROM design/tokens.json (v1.0.0) — DO NOT EDIT BY HAND.
//
// UnoCSS theme adapter. The contract's reference adapters target Tailwind v4
// (`@theme`) or v3 (`tailwind-tokens.cjs`); this project runs UnoCSS, so the
// functional equivalent is this theme object.
//
// Usage (wired only after the namespace migration — see design-system.md § Provenance):
//   import { theme } from '../../design/adapters/uno-tokens.mjs'
//   export default defineConfig({ theme, ... })
//
// Colour namespaces are the top-level groups of `tokens.json § color.*`
// (brand · neutral · sepia · semantic · domain). This is what makes
// `lint-core.mjs` able to validate `bg-semantic-surface` / `text-domain-npc`:
// the head segment of a colour utility MUST be one of these groups.
//
// Alpha modifiers (`bg-brand-primary/10`) work because every colour resolves to
// `rgb(var(--…-rgb) / <alpha-value>)` rather than a hex literal.
//
// `spacing` is deliberately NOT overridden. UnoCSS's native scale (0.25rem unit,
// with half-steps) already yields the frozen 2px step: p-1.5 = 6px, p-2.5 = 10px,
// p-3.5 = 14px. Remapping the keys would silently redefine p-4 from 16px to 4px
// across every existing template.

// ÉCHELLES NON INJECTÉES — fontSize · lineHeight · letterSpacing · borderRadius · maxWidth
//
// Même raison que `spacing` : ces clés existent déjà nativement dans UnoCSS avec
// des valeurs DIFFÉRENTES. Les écraser redéfinit silencieusement les classes de
// tout le projet — `text-sm` passerait de 14px à 13px, `text-base` de 16 à 14,
// `rounded-lg` de 8 à 12, `leading-tight` de 1.25 à 1.15.
//
// Les valeurs du contrat restent disponibles :
//   - en CSS via var(--font-size-body), var(--radius-lg), var(--line-height-base)…
//   - en classe arbitraire : text-[length:var(--font-size-body)]
//
// L'échelle typographique du contrat (caption 12 · sm 13 · base 14 · body 16)
// s'appliquera à l'intégration de la maquette v3, qui porte ses propres tailles.
// Correspondances natives utiles : rounded-lg = 8px (radius.md, boutons),
// rounded-xl = 12px (radius.lg, cartes).

const rgb = (name) => `rgb(var(--color-${name}-rgb) / <alpha-value>)`

// NOTE — les couleurs composées DOIVENT être imbriquées, jamais aplaties avec un
// tiret. UnoCSS résout `bg-semantic-ink-secondary` en descendant l'arbre
// (semantic → ink → secondary) ; une clé plate `'ink-secondary'` ne matche pas et
// la classe ne génère AUCUN css, sans erreur. DEFAULT porte la valeur de base.
export const theme = {
  colors: {
    brand: {
      DEFAULT: rgb('brand-primary'),
      primary: {
        DEFAULT: rgb('brand-primary'),
        hover: rgb('brand-primary-hover'),
      },
      identity: rgb('brand-identity'),
      accent: rgb('brand-accent'),
      signal: {
        DEFAULT: rgb('brand-signal'),
        text: rgb('brand-signal-text'),
      },
    },
    neutral: {
      0: rgb('neutral-0'),
      50: rgb('neutral-50'),
      100: rgb('neutral-100'),
      200: rgb('neutral-200'),
      300: rgb('neutral-300'),
      500: rgb('neutral-500'),
      700: rgb('neutral-700'),
      900: rgb('neutral-900'),
    },
    sepia: {
      50: rgb('sepia-50'),
      300: rgb('sepia-300'),
      500: rgb('sepia-500'),
      600: rgb('sepia-600'),
      700: rgb('sepia-700'),
      800: rgb('sepia-800'),
      900: rgb('sepia-900'),
    },
    semantic: {
      background: rgb('semantic-background'),
      surface: rgb('semantic-surface'),
      card: {
        DEFAULT: rgb('semantic-card'),
        sunken: rgb('semantic-card-sunken'),
      },
      border: rgb('semantic-border'),
      ink: {
        DEFAULT: rgb('semantic-ink'),
        secondary: rgb('semantic-ink-secondary'),
      },
      muted: rgb('semantic-muted'),
      focus: rgb('semantic-focus'),
      success: rgb('semantic-success'),
      warning: rgb('semantic-warning'),
      danger: rgb('semantic-danger'),
      info: rgb('semantic-info'),
    },
    // Iconographie du sélecteur de thème — pas une couleur du système.
    ui: {
      sun: {
        DEFAULT: rgb('ui-sun'),
        soft: rgb('ui-sun-soft'),
      },
      moon: rgb('ui-moon'),
    },
    domain: {
      pc: rgb('domain-pc'),
      npc: rgb('domain-npc'),
      available: {
        DEFAULT: rgb('domain-available'),
        text: rgb('domain-available-text'),
      },
      remote: rgb('domain-remote'),
      claimed: rgb('domain-claimed'),
      adopted: rgb('domain-adopted'),
      forked: rgb('domain-forked'),
      oracle: rgb('domain-oracle'),
      quoted: rgb('domain-quoted'),
    },
  },
  fontFamily: {
    sans: 'var(--font-sans)',
    display: 'var(--font-display)',
    mono: 'var(--font-mono)',
  },
  fontWeight: {
    regular: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },
  boxShadow: {
    card: 'var(--shadow-card)',
    'card-hover': 'var(--shadow-card-hover)',
  },
  borderWidth: {
    hairline: 'var(--border-width-hairline)',
    ring: 'var(--border-width-ring)',
    thick: 'var(--border-width-thick)',
    heavy: 'var(--border-width-heavy)',
  },
  duration: {
    fast: 'var(--duration-fast)',
    base: 'var(--duration-base)',
    slow: 'var(--duration-slow)',
  },
  easing: {
    standard: 'var(--easing-standard)',
    entrance: 'var(--easing-entrance)',
  },
  // Media breakpoints. Layout is driven by @container (app) at the same widths —
  // these exist for the rare case a viewport query is genuinely required.
  breakpoints: {
    xs: '480px',
    sm: '640px',
    md: '768px',
    lg: '1024px',
    xl: '1280px',
  },
  // Seuils de CONTENEUR — volontairement identiques aux breakpoints media.
  // Le conteneur `app` est posé sur <body> : à la racine, sa largeur inline EST
  // celle du viewport, donc la migration @media -> @container est neutre au
  // niveau page, et devient utile dès qu'un composant est placé dans une colonne
  // plus étroite que la fenêtre (une carte dans une grille à 4 colonnes).
  //
  // ATTENTION — la valeur doit être la CONDITION COMPLÈTE, pas la largeur seule.
  // UnoCSS l'interpole telle quelle : `@container ${valeur}`. Avec '640px' il
  // produit `@container 640px{…}`, une at-rule INVALIDE que le navigateur ignore
  // en silence — tout le responsive tombe alors à une seule colonne, sans erreur
  // de build. Avec '(min-width: 640px)' il produit une règle valide.
  containers: {
    xs: '(min-width: 480px)',
    sm: '(min-width: 640px)',
    md: '(min-width: 768px)',
    lg: '(min-width: 1024px)',
    xl: '(min-width: 1280px)',
  },
  zIndex: {
    sticky: '40',
    header: '50',
    dropdown: '60',
    overlay: '80',
    modal: '100',
    toast: '120',
  },
}

export default theme
