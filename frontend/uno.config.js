import {
  defineConfig,
  presetUno,
  presetIcons,
  presetTypography,
  transformerDirectives,
} from 'unocss'

// =================================================================
// Preset Suddenly - Couleurs et tokens custom (dark cosmos)
// =================================================================
const presetSuddenly = () => ({
  name: 'suddenly',
  theme: {
    colors: {
      // CSS variable-driven palette — adapts to light/dark mode via [data-theme]
      background: 'var(--c-bg)',
      surface: 'var(--c-surface)',
      card: {
        DEFAULT: 'var(--c-card)',
        dark: 'var(--c-card-dark)',
      },
      border: 'var(--c-border)',
      primary: 'var(--c-primary)',
      secondary: 'var(--c-secondary)',
      muted: 'var(--c-muted)',
      // Action colors — CSS var driven, supports opacity modifiers (bg-crimson/10)
      crimson: {
        DEFAULT: 'rgb(var(--c-crimson) / <alpha-value>)',
        hover: 'rgb(var(--c-crimson-hover) / <alpha-value>)',
      },
      violet: {
        DEFAULT: 'rgb(var(--c-violet) / <alpha-value>)',
        hover: 'rgb(var(--c-violet-hover) / <alpha-value>)',
      },
      neon: {
        DEFAULT: 'rgb(var(--c-neon) / <alpha-value>)',
        hover: 'rgb(var(--c-neon-hover) / <alpha-value>)',
      },
      brand: {
        DEFAULT: 'rgb(var(--c-brand) / <alpha-value>)',
        hover: 'rgb(var(--c-brand-hover) / <alpha-value>)',
      },
      // Semantic feedback — adaptive per mode via base.css CSS vars
      success: 'rgb(var(--c-success) / <alpha-value>)',
      warning: 'rgb(var(--c-warning) / <alpha-value>)',
      error: 'rgb(var(--c-error) / <alpha-value>)',
      info: 'rgb(var(--c-info) / <alpha-value>)',

      // Statuts des personnages — utilisés par les badges badge-*
      // (conservés comme référence sémantique, les badges utilisent les palettes Tailwind)
    },

    // Fonts
    fontFamily: {
      sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      serif: ['Crimson Text', 'Georgia', 'serif'],
      mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
    },

    // Espacements custom
    spacing: {
      'safe': 'env(safe-area-inset-bottom)',
    },

    // Border radius
    borderRadius: {
      'card': '0.75rem',
      'button': '0.5rem',
      'badge': '9999px',
    },

    // Shadows
    boxShadow: {
      'card': 'var(--shadow-card)',
      'card-hover': 'var(--shadow-card-hover)',
      'dropdown': '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
      'btn': '0 4px 20px rgba(224,53,88,0.35)',
    },

    // Z-index scale
    zIndex: {
      'dropdown': '10',
      'sticky': '20',
      'overlay': '30',
      'modal': '40',
      'toast': '50',
    },

    // Animation durations — respects prefers-reduced-motion via CSS fallback
    duration: {
      'fast': '100ms',
      'normal': '200ms',
      'slow': '300ms',
    },

    // Easing
    easing: {
      'in': 'cubic-bezier(0.4, 0, 1, 1)',
      'out': 'cubic-bezier(0, 0, 0.2, 1)',
      'in-out': 'cubic-bezier(0.4, 0, 0.2, 1)',
    },
  },

  // Shortcuts - classes réutilisables
  shortcuts: {
    // Layout
    'container-app': 'max-w-7xl mx-auto px-4 sm:px-6 lg:px-8',

    // Boutons
    'btn-primary': 'inline-flex items-center justify-center gap-2 bg-crimson text-white px-7 py-[13px] text-[15px] font-semibold rounded-[12px] transition-all duration-250 hover:bg-crimson-hover hover:-translate-y-0.5 hover:shadow-btn focus-visible:outline-none disabled:opacity-50 disabled:cursor-not-allowed',
    'btn-secondary': 'inline-flex items-center justify-center gap-2 bg-transparent border border-border text-secondary px-7 py-[13px] text-[15px] font-semibold rounded-[12px] transition-all duration-250 hover:border-crimson hover:text-crimson hover:-translate-y-0.5 focus-visible:outline-none disabled:opacity-50 disabled:cursor-not-allowed',
    'btn-ghost': 'inline-flex items-center justify-center gap-2 bg-transparent text-secondary hover:text-primary transition-colors focus-visible:outline-none disabled:opacity-50 disabled:cursor-not-allowed',
    'btn-danger': 'inline-flex items-center justify-center gap-2 bg-error text-white px-7 py-[13px] text-[15px] font-semibold rounded-[12px] transition-all duration-250 hover:bg-error/90 focus-visible:outline-none disabled:opacity-50 disabled:cursor-not-allowed',
    'btn-sm': 'px-3 py-1.5 text-sm',
    'btn-lg': 'px-6 py-3 text-lg',

    // Cards
    'card': 'bg-card border border-border rounded-2xl p-6',
    'card-hover': 'card hover:shadow-card-hover hover:border-crimson/30 hover:-translate-y-0.5 transition-all cursor-pointer',
    'card-body': 'p-4 sm:p-6',
    'card-header': 'px-4 py-3 sm:px-6 border-b border-border',
    'card-footer': 'px-4 py-3 sm:px-6 border-t border-border rounded-b-card',

    // Formulaires
    'input-base': 'bg-violet/10 border border-violet/30 rounded-[12px] text-primary placeholder-muted focus:border-crimson outline-none',
    'form-input': 'block w-full rounded-[12px] border border-violet/30 px-3 py-2.5 focus:border-crimson sm:text-sm bg-violet/10 text-primary outline-none',
    'form-input-error': 'form-input bg-error/10 border-error focus:border-error',
    'form-label': 'block text-sm font-medium text-secondary mb-1',
    'form-help': 'mt-1 text-sm text-muted',
    'form-error': 'mt-1 text-sm text-error',
    'form-select': 'form-input appearance-none cursor-pointer pr-10',
    'form-dropzone': 'mt-1 flex flex-col items-center justify-center gap-1 px-6 pt-5 pb-6 border-2 border-border border-dashed rounded-lg hover:border-crimson transition-colors',
    'form-dropzone-link': 'relative cursor-pointer rounded-md font-medium text-crimson hover:text-crimson-hover focus-within:outline-none',

    // Switch (remplace checkbox)
    'switch-track': 'relative inline-flex h-6 w-11 shrink-0 items-center rounded-full p-0.5 transition-colors duration-200 focus-visible:outline-none cursor-pointer',
    'switch-thumb': 'inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-200',

    // Badges
    'badge': 'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-badge text-xs font-medium',

    // Badges de statut personnage — couleurs sémantiques, compatibles light/dark
    'badge-available': 'badge bg-success/10 text-success border border-success/30',
    'badge-claimed': 'badge bg-crimson/10 text-crimson border border-crimson/30',
    'badge-adopted': 'badge bg-info/10 text-info border border-info/30',
    'badge-forked': 'badge bg-warning/10 text-warning border border-warning/30',
    'badge-info': 'badge bg-info/10 text-info border border-info/30',
    'badge-pending': 'badge bg-surface text-muted border border-border',
    'badge-rejected': 'badge bg-error/10 text-error border border-error/30',
    'badge-pc': 'badge bg-sky-900/40 text-sky-400 border border-sky-700/50',
    'badge-primary': 'badge bg-crimson/10 text-crimson border border-crimson/30',
    'badge-gray': 'badge bg-surface text-muted border border-border',
    'badge-accent': 'badge bg-warning/10 text-warning border border-warning/30',

    // Avatars
    'avatar': 'rounded-full object-cover bg-surface',
    'avatar-sm': 'avatar w-8 h-8',
    'avatar-md': 'avatar w-10 h-10',
    'avatar-lg': 'avatar w-12 h-12',
    'avatar-xl': 'avatar w-16 h-16',
    'avatar-placeholder': 'avatar flex items-center justify-center bg-surface text-secondary',

    // Dropdown menu
    'dropdown-menu': 'absolute bg-surface border border-border rounded-[12px] shadow-lg py-1 z-dropdown',

    // Links
    'link': 'text-crimson hover:text-crimson-hover hover:underline',
    'link-muted': 'text-secondary hover:text-primary',

    // Text
    'text-heading': 'text-primary font-semibold',

    // Label overline
    'label-overline': 'text-crimson text-[12px] font-medium tracking-[3px] uppercase',

    // Prose (pour les reports)
    'prose-report': 'prose max-w-none',
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
      // Collections d'icônes
      collections: {
        lucide: () => import('@iconify-json/lucide/icons.json').then(i => i.default),
        'simple-icons': () => import('@iconify-json/simple-icons/icons.json').then(i => i.default),
        'game-icons': () => import('@iconify-json/game-icons/icons.json').then(i => i.default),
      },
    }),
    presetTypography({
      cssExtend: {
        'a': {
          'color': 'rgb(var(--c-crimson))',
          'text-decoration': 'none',
        },
        'a:hover': {
          'text-decoration': 'underline',
        },
        'blockquote': {
          'border-left-color': 'rgb(var(--c-crimson))',
          'font-style': 'normal',
        },
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
    'bg-success/10', 'bg-error/10', 'bg-warning/10', 'bg-info/10',
    'border-success/30', 'border-error/30', 'border-warning/30', 'border-info/30',
    'text-success', 'text-error', 'text-warning', 'text-info',
    'hover:bg-error/10', 'hover:bg-card',
    'bg-violet/10', 'text-violet', 'border-violet/30',
    // Z-index sémantiques (custom tokens)
    'z-dropdown', 'z-sticky', 'z-overlay', 'z-modal', 'z-toast',
    // Game Icons — empty states thématiques
    'i-game-icons-open-book', 'i-game-icons-scroll-quill', 'i-game-icons-two-shadows',
    'i-game-icons-chat-bubble', 'i-game-icons-dice-six-faces-four',
    'i-game-icons-manacles', 'i-game-icons-hand', 'i-game-icons-divergence',
    // Icônes fréquentes (utilisées dans des template tags dynamiques)
    'i-lucide-user', 'i-lucide-users', 'i-lucide-book-open', 'i-lucide-link',
    'i-lucide-git-merge', 'i-lucide-git-branch', 'i-lucide-sparkles',
    'i-lucide-plus', 'i-lucide-edit', 'i-lucide-trash', 'i-lucide-check',
    'i-lucide-x', 'i-lucide-search', 'i-lucide-menu', 'i-lucide-bell',
    'i-lucide-cloud', 'i-lucide-cloud-off', 'i-lucide-loader-2',
    'i-lucide-alert-triangle', 'i-lucide-info',
    'i-lucide-sun', 'i-lucide-moon',
    // Couleur brand (logo #6364FF)
    'text-brand', 'bg-brand', 'bg-brand/10', 'bg-brand/15', 'border-brand', 'border-brand/30',
    // Couleurs neon (neon accent)
    'text-neon', 'bg-neon/10', 'border-neon/30',
    // Couleurs crimson (accent primaire)
    'bg-crimson', 'bg-crimson/10',
    'border-crimson', 'border-crimson/30', 'border-crimson/50',
    'text-crimson', 'text-crimson/80',
    'hover:bg-crimson/10',
    // Couleurs violet/crimson pour composants dark-light
    'bg-violet', 'border-violet', 'hover:text-violet/60',
    // Theme toggle + form switch (Alpine :class bindings)
    'translate-x-0', 'translate-x-6', 'translate-x-8', 'bg-amber-400', 'bg-muted',
    'border-crimson/50', 'border-violet/50', 'border-amber-300/60', 'text-amber-400',
    // Badges dynamiques pending/rejected
    'badge-pending', 'badge-rejected',
    // Character card portrait aspect ratio
    'aspect-[2/3]',
  ],
})
