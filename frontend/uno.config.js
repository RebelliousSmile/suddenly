import {
  defineConfig,
  presetUno,
  presetIcons,
  presetTypography,
  transformerDirectives,
} from 'unocss'

import { theme as contractTheme } from '../design/adapters/uno-tokens.mjs'

// =================================================================
// Preset Suddenly — thème dérivé du contrat de design
//
// Source de vérité : design/tokens.json (v1.0.0).
// L'adapter design/adapters/uno-tokens.mjs est GÉNÉRÉ — ne pas l'éditer.
// Les variables CSS viennent de design/adapters/tokens.css (importé par main.js).
//
// Les namespaces de couleur (brand · neutral · sepia · semantic · domain) sont
// les groupes top-level de tokens.json § color.* — c'est ce qui rend le lint
// du contrat capable de vérifier `bg-semantic-surface` / `text-domain-npc`.
//
// `spacing` n'est PAS surchargé : l'échelle native d'UnoCSS (0.25rem, demi-pas)
// produit déjà le pas de 2px figé (p-1.5 = 6px, p-2.5 = 10px). La remapper
// redéfinirait p-4 de 16px à 4px dans tous les templates.
// =================================================================
const presetSuddenly = () => ({
  name: 'suddenly',
  theme: {
    ...contractTheme,

    // fontFamily — Fraunces est la serif de fiction du contrat (font.family.display).
    // `serif` et `display` pointent sur la même famille : les 34 usages historiques
    // de `font-serif` sont exactement les endroits de fiction, ils n'ont pas à être
    // renommés. Crimson Text est retirée : elle n'a plus aucun usage.
    // `mono` n'est pas self-hostée — repli sur la mono du système.
    fontFamily: {
      sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      serif: ['Fraunces', 'Georgia', 'serif'],
      display: ['Fraunces', 'Georgia', 'serif'],
      mono: ['JetBrains Mono', 'Fira Code', 'ui-monospace', 'monospace'],
    },

    // Espacements custom — insets d'encoche (safe-area) sur les 4 côtés,
    // pour les barres collantes et le contenu en bord d'écran (mobile #6/#7).
    spacing: {
      'safe': 'env(safe-area-inset-bottom)',
      'safe-t': 'env(safe-area-inset-top)',
      'safe-b': 'env(safe-area-inset-bottom)',
      'safe-l': 'env(safe-area-inset-left)',
      'safe-r': 'env(safe-area-inset-right)',
    },

    // Ombres : le contrat couvre card / card-hover.
    // btn et dropdown n'ont pas de token — conservées en extension.
    boxShadow: {
      ...contractTheme.boxShadow,
      dropdown: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
      btn: '0 4px 20px rgba(224,53,88,0.35)',
    },
  },

  // Shortcuts — classes réutilisables
  shortcuts: {
    // Layout
    'container-app': 'max-w-7xl mx-auto px-4 @sm:px-6 @lg:px-8',

    // Focus — figé par le contrat (focus.*) : 2px, offset 2px, indigo.
    // Indigo et non crimson : 4,5:1 contre 4,2:1, et pour ne pas confondre
    // « ceci a le focus » avec « ceci est l'action primaire ».
    'focus-ring': 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-semantic-focus focus-visible:ring-offset-2 focus-visible:ring-offset-semantic-background',

    // Grilles fluides (mobile-first) — se replient sur la largeur réelle du
    // conteneur plutôt que sur des breakpoints d'écran fixes, ce qui évite le
    // débordement horizontal des cartes sur petits écrans (< 360px).
    // grid-stats : bandes de compteurs (peu d'items → auto-fit remplit la largeur)
    // grid-cards : listes de cartes personnage (largeur de carte stable → auto-fill)
    'grid-stats': 'grid gap-4 grid-cols-[repeat(auto-fit,minmax(140px,1fr))]',
    'grid-cards': 'grid gap-3 grid-cols-[repeat(auto-fill,minmax(150px,1fr))]',

    // Boutons
    'btn-primary': 'inline-flex items-center justify-center gap-2 bg-brand-primary text-white px-7 py-[13px] text-[15px] font-semibold rounded-lg transition-all duration-250 hover:bg-brand-primary-hover hover:-translate-y-0.5 hover:shadow-btn focus-ring disabled:opacity-50 disabled:cursor-not-allowed',
    'btn-secondary': 'inline-flex items-center justify-center gap-2 bg-transparent border border-semantic-border text-semantic-ink-secondary px-7 py-[13px] text-[15px] font-semibold rounded-lg transition-all duration-250 hover:border-brand-primary hover:text-brand-primary hover:-translate-y-0.5 focus-ring disabled:opacity-50 disabled:cursor-not-allowed',
    'btn-ghost': 'inline-flex items-center justify-center gap-2 bg-transparent text-semantic-ink-secondary hover:text-semantic-ink transition-colors focus-ring disabled:opacity-50 disabled:cursor-not-allowed',
    'btn-danger': 'inline-flex items-center justify-center gap-2 bg-semantic-danger text-white px-7 py-[13px] text-[15px] font-semibold rounded-lg transition-all duration-250 hover:bg-semantic-danger/90 focus-ring disabled:opacity-50 disabled:cursor-not-allowed',
    'btn-sm': 'px-3 py-1.5 text-sm',
    'btn-lg': 'px-6 py-3 text-lg',
    // Cible tactile ≥ 44px pour les boutons d'action compacts sur mobile (#6).
    'tap-target': 'min-h-11 min-w-11 inline-flex items-center justify-center',
    // Barre d'action de l'éditeur (#7) : collante en bas sur mobile (avec
    // safe-area), redevient inline à partir de sm.
    'editor-actions': 'flex items-center gap-3 sticky bottom-0 -mx-4 px-4 py-3 bg-semantic-surface border-t border-semantic-border pb-safe z-sticky sm:static sm:mx-0 sm:px-0 sm:py-0 sm:bg-transparent sm:border-0',

    // Cards
    'card': 'bg-semantic-card border border-semantic-border rounded-xl p-6',
    'card-hover': 'card hover:shadow-card-hover hover:border-brand-primary/30 hover:-translate-y-0.5 transition-all cursor-pointer',
    'card-body': 'p-4 @sm:p-6',
    'card-header': 'px-4 py-3 @sm:px-6 border-b border-semantic-border',
    'card-footer': 'px-4 py-3 @sm:px-6 border-t border-semantic-border rounded-b-xl',

    // Formulaires
    'input-base': 'appearance-none bg-semantic-surface border border-solid border-semantic-border rounded-lg text-semantic-ink placeholder-semantic-muted focus:border-brand-primary outline-none',
    'form-input': 'appearance-none block w-full min-w-0 rounded-lg border border-solid border-semantic-border px-3 py-2.5 focus:border-brand-primary @sm:text-sm bg-semantic-surface text-semantic-ink outline-none',
    'form-input-error': 'form-input bg-semantic-danger/10 border-semantic-danger focus:border-semantic-danger',
    'form-label': 'block text-sm font-medium text-semantic-ink-secondary mb-1',
    'form-help': 'mt-1 text-sm text-semantic-muted',
    'form-error': 'mt-1 text-sm text-semantic-danger',
    'form-select': 'form-input appearance-none cursor-pointer pr-10',
    'form-dropzone': 'mt-1 flex flex-col items-center justify-center gap-1 px-6 pt-5 pb-6 border-2 border-semantic-border border-dashed rounded-lg hover:border-brand-primary transition-colors',
    'form-dropzone-link': 'relative cursor-pointer rounded-md font-medium text-brand-primary hover:text-brand-primary-hover focus-within:outline-none',

    // Switch (remplace checkbox)
    'switch-track': 'relative inline-flex h-6 w-11 shrink-0 items-center rounded-full p-0.5 border border-semantic-border transition-colors duration-200 focus-ring cursor-pointer',
    'switch-thumb': 'inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-200',

    // Badges
    'badge': 'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium',

    // Badges de statut personnage — tokens color.domain.*
    // available : le fond et la bordure prennent le signal vif (seuil 3:1),
    // le TEXTE prend domain-available-text (#0a8f4d) — le néon ne porte
    // jamais de glyphe (1,6:1). Règle figée : usage.rules[signal-never-text].
    'badge-available': 'badge bg-brand-signal/10 text-domain-available-text border border-brand-signal/30',
    'badge-claimed': 'badge bg-domain-claimed/10 text-domain-claimed border border-domain-claimed/30',
    'badge-adopted': 'badge bg-domain-adopted/10 text-domain-adopted border border-domain-adopted/30',
    'badge-forked': 'badge bg-domain-forked/10 text-domain-forked border border-domain-forked/30',
    'badge-info': 'badge bg-semantic-info/10 text-semantic-info border border-semantic-info/30',
    'badge-pending': 'badge bg-semantic-surface text-semantic-muted border border-semantic-border',
    'badge-rejected': 'badge bg-semantic-danger/10 text-semantic-danger border border-semantic-danger/30',
    'badge-pc': 'badge bg-domain-pc/10 text-domain-pc border border-domain-pc/30',
    'badge-primary': 'badge bg-brand-primary/10 text-brand-primary border border-brand-primary/30',
    'badge-gray': 'badge bg-semantic-surface text-semantic-muted border border-semantic-border',
    'badge-accent': 'badge bg-semantic-warning/10 text-semantic-warning border border-semantic-warning/30',

    // Avatars
    'avatar': 'rounded-full object-cover bg-semantic-surface',
    'avatar-sm': 'avatar w-8 h-8',
    'avatar-md': 'avatar w-10 h-10',
    'avatar-lg': 'avatar w-12 h-12',
    'avatar-xl': 'avatar w-16 h-16',
    'avatar-placeholder': 'avatar flex items-center justify-center bg-semantic-surface text-semantic-ink-secondary',

    // Dropdown menu
    'dropdown-menu': 'absolute bg-semantic-surface border border-semantic-border rounded-xl shadow-xl ring-1 ring-black/10 py-1 z-dropdown',

    // Links
    'link': 'text-brand-primary hover:text-brand-primary-hover hover:underline',
    'link-muted': 'text-semantic-ink-secondary hover:text-semantic-ink',

    // Text
    'text-heading': 'text-semantic-ink font-semibold',

    // Label overline
    'label-overline': 'text-brand-primary text-[12px] font-medium tracking-[3px] uppercase',

    // Prose (pour les reports)
    'prose-report': 'prose max-w-none',

    // pick-sheet — modale de choix d'un élément dans une liste (contrat : components.json).
    // Paire mobile→desktop sanctionnée : bottom-sheet plein écran → panneau ancré au déclencheur.
    // `-fixed` : collée au bas du viewport, pleine largeur — le mode scène
    // (frozen) en dépend, aucun conteneur de scroll ne peut la clipper.
    // Défaut (feed) : identique en mobile ; à partir de @lg (sidebar visible)
    // elle devient un panneau ancré au <form> (@lg:relative) → largeur = colonne
    // du composer = sidebar, ancré en haut, jamais pleine largeur d'écran.
    'pick-sheet-fixed': 'fixed inset-x-0 bottom-0 z-modal card rounded-t-2xl shadow-lg max-h-[82vh] overflow-y-auto px-3',
    'pick-sheet': 'pick-sheet-fixed @lg:absolute @lg:top-0 @lg:bottom-auto @lg:rounded-2xl',
  },
})

// =================================================================
// Configuration UnoCSS
// =================================================================
export default defineConfig({
  presets: [
    presetUno(),
    presetSuddenly(),
    presetIcons({
      scale: 1.2,
      extraProperties: {
        'display': 'inline-block',
        'vertical-align': 'middle',
      },
      // Trois collections, trois rôles :
      //   lucide      → toutes les icônes d'INTERFACE (jeu unique du contrat)
      //   simple-icons→ logos de marques tierces (pas des icônes d'UI)
      //   game-icons  → illustrations décoratives d'états vides
      // Divergence assumée avec icon.library=lucide — cf. design-system.md § Open questions.
      collections: {
        lucide: () => import('@iconify-json/lucide/icons.json').then(i => i.default),
        'simple-icons': () => import('@iconify-json/simple-icons/icons.json').then(i => i.default),
        'game-icons': () => import('@iconify-json/game-icons/icons.json').then(i => i.default),
      },
    }),
    presetTypography({
      cssExtend: {
        'a': {
          'color': 'var(--color-brand-primary)',
          'text-decoration': 'none',
        },
        'a:hover': {
          'text-decoration': 'underline',
        },
        'h1': { 'color': 'var(--color-semantic-ink)' },
        'h2': { 'color': 'var(--color-semantic-ink)' },
        'h3': { 'color': 'var(--color-semantic-ink)' },
        'h4,h5,h6': { 'color': 'var(--color-semantic-ink-secondary)' },
        'strong': { 'color': 'var(--color-semantic-ink)' },
        'em': { 'color': 'var(--color-semantic-ink-secondary)' },
        'code': {
          // Le néon ne porte jamais de glyphe : le texte du code prend la
          // variante assombrie (domain-available-text). Le fond garde le signal.
          'color': 'var(--color-domain-available-text)',
          'background': 'rgb(var(--color-brand-signal-rgb) / 0.08)',
          'border-radius': '0.3rem',
          'padding': '0.1em 0.4em',
        },
        'pre code': {
          'color': 'inherit',
          'background': 'transparent',
          'padding': '0',
        },
        'blockquote': {
          'border-left-color': 'var(--color-brand-primary)',
          'font-style': 'normal',
          'color': 'var(--color-semantic-ink-secondary)',
        },
        'ul > li::marker': { 'color': 'var(--color-semantic-ink-secondary)' },
        'ol > li::marker': { 'color': 'var(--color-semantic-ink-secondary)' },
      },
    }),
  ],

  transformers: [
    transformerDirectives(),  // Permet @apply dans le CSS
  ],

  // Scanner les templates Django
  content: {
    filesystem: [
      '../templates/**/*.html',
      '../suddenly/**/*.py',  // Pour les classes dans les views
    ],
  },

  // Safelist - classes toujours incluses
  // IMPORTANT: toute classe générée dynamiquement en Python (template tags,
  // context variables) DOIT être ajoutée ici. Le scanner UnoCSS ne détecte
  // que les classes présentes littéralement dans les fichiers HTML/PY.
  safelist: [
    // Statuts dynamiques (générés via character.status dans les templates)
    'badge-available', 'badge-claimed', 'badge-adopted', 'badge-forked', 'badge-pc', 'badge-info',
    // Modificateurs d'opacité (classes dynamiques dans expressions Django, non détectables par le scanner)
    'bg-semantic-success/10', 'bg-semantic-danger/10', 'bg-semantic-warning/10', 'bg-semantic-info/10',
    'border-semantic-success/30', 'border-semantic-danger/30', 'border-semantic-warning/30', 'border-semantic-info/30',
    'text-semantic-success', 'text-semantic-danger', 'text-semantic-warning', 'text-semantic-info',
    'hover:bg-semantic-danger/10', 'hover:bg-semantic-card',
    'bg-brand-accent/10', 'text-brand-accent', 'border-brand-accent/30',
    // Z-index sémantiques (custom tokens)
    'z-dropdown', 'z-sticky', 'z-header', 'z-overlay', 'z-modal', 'z-toast',
    // Game Icons — empty states thématiques
    'i-game-icons-open-book', 'i-game-icons-scroll-quill', 'i-game-icons-two-shadows',
    'i-game-icons-chat-bubble', 'i-game-icons-dice-six-faces-four',
    'i-game-icons-manacles', 'i-game-icons-hand', 'i-game-icons-divergence',
    'i-game-icons-hooded-figure', 'i-game-icons-monk-face',
    // Icônes fréquentes (utilisées dans des template tags dynamiques)
    'i-lucide-user', 'i-lucide-users', 'i-lucide-book-open', 'i-lucide-link',
    'i-lucide-git-merge', 'i-lucide-git-branch', 'i-lucide-sparkles',
    'i-lucide-plus', 'i-lucide-edit', 'i-lucide-trash', 'i-lucide-check',
    'i-lucide-x', 'i-lucide-search', 'i-lucide-menu', 'i-lucide-bell',
    'i-lucide-cloud', 'i-lucide-cloud-off', 'i-lucide-loader-2',
    'i-lucide-alert-triangle', 'i-lucide-info',
    'i-lucide-sun', 'i-lucide-moon',
    // Identité (PJ, mention, logo) — color.domain.pc / color.brand.identity
    'text-domain-pc', 'bg-domain-pc', 'bg-domain-pc/10', 'bg-domain-pc/15',
    'border-domain-pc', 'border-domain-pc/30',
    // Card sunken (option C formulaires)
    'bg-semantic-card-sunken',
    // Signal de disponibilité — jamais de texte sur le néon
    'text-domain-available-text', 'bg-brand-signal/10', 'border-brand-signal/30',
    // Action primaire
    'bg-brand-primary', 'bg-brand-primary/10',
    'border-brand-primary', 'border-brand-primary/30', 'border-brand-primary/50',
    'text-brand-primary', 'text-brand-primary/80',
    'hover:bg-brand-primary/10',
    // Fédération / fork / oracle
    'bg-brand-accent', 'border-brand-accent', 'hover:text-brand-accent/60',
    // Theme toggle + form switch (Alpine :class bindings)
    'translate-x-0', 'translate-x-5', 'translate-x-6', 'translate-x-8',
    'bg-ui-sun', 'bg-semantic-muted',
    'border-brand-primary/50', 'border-brand-accent/50', 'border-ui-sun-soft/60', 'text-ui-sun',
    // Badges dynamiques pending/rejected
    'badge-pending', 'badge-rejected',
    // Character card portrait aspect ratio
    'aspect-[2/3]',
  ],
})
