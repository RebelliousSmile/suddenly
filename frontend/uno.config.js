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
      // Dark cosmos palette
      background: '#0a0915',
      surface: '#100e20',
      card: {
        DEFAULT: '#18162a',
        dark: '#211e36',
      },
      border: '#2d2845',
      primary: '#ede8f5',
      secondary: '#b0a8cc',
      muted: '#7a7290',
      crimson: {
        DEFAULT: '#e03558',
        hover: '#c82a4a',
      },
      success: '#16a34a',
      warning: '#d97706',
      error: '#e03558',
      info: '#6366f1',

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
      'card': '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
      'card-hover': '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
      'dropdown': '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
      'btn': '0 4px 20px rgba(224, 53, 88, 0.35)',
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
    'btn-primary': 'inline-flex items-center justify-center gap-2 bg-crimson text-white px-7 py-[13px] text-[15px] font-semibold rounded-[12px] transition-all duration-250 hover:bg-crimson-hover hover:-translate-y-0.5 hover:shadow-btn disabled:opacity-50 disabled:cursor-not-allowed',
    'btn-secondary': 'inline-flex items-center justify-center gap-2 bg-transparent border border-border text-secondary px-7 py-[13px] text-[15px] font-semibold rounded-[12px] transition-all duration-250 hover:border-crimson hover:text-crimson hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed',
    'btn-ghost': 'inline-flex items-center justify-center gap-2 bg-transparent text-secondary hover:text-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed',
    'btn-danger': 'inline-flex items-center justify-center gap-2 bg-error text-white px-7 py-[13px] text-[15px] font-semibold rounded-[12px] transition-all duration-250 hover:bg-error/90 disabled:opacity-50 disabled:cursor-not-allowed',
    'btn-sm': 'px-3 py-1.5 text-sm',
    'btn-lg': 'px-6 py-3 text-lg',

    // Cards
    'card': 'bg-card border border-border rounded-2xl p-6',
    'card-hover': 'card hover:shadow-card-hover transition-shadow',
    'card-body': 'p-4 sm:p-6',
    'card-header': 'px-4 py-3 sm:px-6 border-b border-border',
    'card-footer': 'px-4 py-3 sm:px-6 border-t border-border rounded-b-card',

    // Formulaires
    'input-base': 'bg-card border border-border rounded-[12px] text-primary placeholder-muted focus:border-crimson focus:ring-1 focus:ring-crimson outline-none',
    'form-input': 'block w-full rounded-button border border-border shadow-sm focus:border-crimson focus:ring-crimson sm:text-sm bg-card text-primary',
    'form-input-error': 'form-input border-error focus:border-error focus:ring-error',
    'form-label': 'block text-sm font-medium text-secondary mb-1',
    'form-help': 'mt-1 text-sm text-muted',
    'form-error': 'mt-1 text-sm text-error',
    'form-dropzone': 'mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-border border-dashed rounded-lg hover:border-crimson transition-colors',
    'form-dropzone-link': 'relative cursor-pointer rounded-md font-medium text-crimson hover:text-crimson-hover focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-crimson',

    // Badges
    'badge': 'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-badge text-xs font-medium',

    // Badges de statut personnage — teintes sombres lisibles sur bg-card dark cosmos
    'badge-available': 'badge bg-emerald-900/40 text-emerald-400 border border-emerald-700/50',
    'badge-claimed': 'badge bg-amber-900/40 text-amber-400 border border-amber-700/50',
    'badge-adopted': 'badge bg-indigo-900/40 text-indigo-400 border border-indigo-700/50',
    'badge-forked': 'badge bg-violet-900/40 text-violet-400 border border-violet-700/50',
    'badge-pc': 'badge bg-sky-900/40 text-sky-400 border border-sky-700/50',

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
    'link-muted': 'text-muted hover:text-secondary',

    // Text
    'text-heading': 'text-primary font-semibold',

    // Label overline
    'label-overline': 'text-crimson text-[12px] font-medium tracking-[3px] uppercase',

    // Prose (pour les reports)
    'prose-report': 'prose prose-invert max-w-none',
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
      },
    }),
    presetTypography({
      cssExtend: {
        'a': {
          'color': '#e03558',
          'text-decoration': 'none',
        },
        'a:hover': {
          'text-decoration': 'underline',
        },
        'blockquote': {
          'border-left-color': '#e03558',
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
    'badge-available', 'badge-claimed', 'badge-adopted', 'badge-forked', 'badge-pc',
    // Z-index sémantiques (custom tokens)
    'z-dropdown', 'z-sticky', 'z-overlay', 'z-modal', 'z-toast',
    // Icônes fréquentes (utilisées dans des template tags dynamiques)
    'i-lucide-user', 'i-lucide-users', 'i-lucide-book-open', 'i-lucide-link',
    'i-lucide-git-merge', 'i-lucide-git-branch', 'i-lucide-sparkles',
    'i-lucide-plus', 'i-lucide-edit', 'i-lucide-trash', 'i-lucide-check',
    'i-lucide-x', 'i-lucide-search', 'i-lucide-menu', 'i-lucide-bell',
    'i-lucide-cloud', 'i-lucide-cloud-off', 'i-lucide-loader-2',
    'i-lucide-alert-triangle', 'i-lucide-info',
  ],
})
