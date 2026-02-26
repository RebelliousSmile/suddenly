import {
  defineConfig,
  presetUno,
  presetIcons,
  presetTypography,
  transformerDirectives,
} from 'unocss'

// =================================================================
// Preset Suddenly - Couleurs et tokens custom
// =================================================================
const presetSuddenly = () => ({
  name: 'suddenly',
  theme: {
    colors: {
      // Couleur principale - Indigo/Violet (créativité, fiction)
      primary: {
        50: '#eef2ff',
        100: '#e0e7ff',
        200: '#c7d2fe',
        300: '#a5b4fc',
        400: '#818cf8',
        500: '#6366f1',
        600: '#4f46e5',
        700: '#4338ca',
        800: '#3730a3',
        900: '#312e81',
        950: '#1e1b4b',
      },
      // Secondaire - Emerald (liens, connexions)
      secondary: {
        50: '#ecfdf5',
        100: '#d1fae5',
        200: '#a7f3d0',
        300: '#6ee7b7',
        400: '#34d399',
        500: '#10b981',
        600: '#059669',
        700: '#047857',
        800: '#065f46',
        900: '#064e3b',
        950: '#022c22',
      },
      // Accent - Amber (attention, actions)
      accent: {
        50: '#fffbeb',
        100: '#fef3c7',
        200: '#fde68a',
        300: '#fcd34d',
        400: '#fbbf24',
        500: '#f59e0b',
        600: '#d97706',
        700: '#b45309',
        800: '#92400e',
        900: '#78350f',
        950: '#451a03',
      },
      // Statuts des personnages
      status: {
        available: '#10b981',   // Vert - PNJ disponible
        claimed: '#f59e0b',     // Amber - Réclamé
        adopted: '#6366f1',     // Indigo - Adopté
        forked: '#8b5cf6',      // Violet - Forké
        pc: '#3b82f6',          // Bleu - PJ
      },
    },
    
    // Fonts
    fontFamily: {
      sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      serif: ['Lora', 'Georgia', 'serif'],
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
    },
  },
  
  // Shortcuts - classes réutilisables
  shortcuts: {
    // Layout
    'container-app': 'max-w-7xl mx-auto px-4 sm:px-6 lg:px-8',
    
    // Boutons
    'btn': 'inline-flex items-center justify-center gap-2 px-4 py-2 rounded-button font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed',
    'btn-primary': 'btn bg-primary-600 text-white hover:bg-primary-700 focus:ring-primary-500',
    'btn-secondary': 'btn bg-white text-gray-700 border border-gray-300 hover:bg-gray-50 focus:ring-primary-500',
    'btn-ghost': 'btn text-gray-600 hover:bg-gray-100 focus:ring-gray-500',
    'btn-danger': 'btn bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
    'btn-sm': 'px-3 py-1.5 text-sm',
    'btn-lg': 'px-6 py-3 text-lg',
    
    // Cards
    'card': 'bg-white rounded-card border border-gray-200 shadow-card',
    'card-hover': 'card hover:shadow-card-hover transition-shadow',
    'card-body': 'p-4 sm:p-6',
    'card-header': 'px-4 py-3 sm:px-6 border-b border-gray-200',
    'card-footer': 'px-4 py-3 sm:px-6 border-t border-gray-100 bg-gray-50 rounded-b-card',
    
    // Formulaires
    'form-input': 'block w-full rounded-button border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
    'form-label': 'block text-sm font-medium text-gray-700 mb-1',
    'form-help': 'mt-1 text-sm text-gray-500',
    'form-error': 'mt-1 text-sm text-red-600',
    
    // Badges
    'badge': 'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-badge text-xs font-medium',
    'badge-primary': 'badge bg-primary-100 text-primary-800',
    'badge-secondary': 'badge bg-secondary-100 text-secondary-800',
    'badge-accent': 'badge bg-accent-100 text-accent-800',
    'badge-gray': 'badge bg-gray-100 text-gray-800',
    
    // Badges de statut personnage
    'badge-available': 'badge bg-green-100 text-green-800',
    'badge-claimed': 'badge bg-amber-100 text-amber-800',
    'badge-adopted': 'badge bg-indigo-100 text-indigo-800',
    'badge-forked': 'badge bg-violet-100 text-violet-800',
    'badge-pc': 'badge bg-blue-100 text-blue-800',
    
    // Avatars
    'avatar': 'rounded-full object-cover bg-gray-200',
    'avatar-sm': 'avatar w-8 h-8',
    'avatar-md': 'avatar w-10 h-10',
    'avatar-lg': 'avatar w-12 h-12',
    'avatar-xl': 'avatar w-16 h-16',
    'avatar-placeholder': 'avatar flex items-center justify-center bg-primary-100 text-primary-600',
    
    // Links
    'link': 'text-primary-600 hover:text-primary-800 hover:underline',
    'link-muted': 'text-gray-500 hover:text-gray-700',
    
    // Text
    'text-muted': 'text-gray-500',
    'text-heading': 'text-gray-900 font-semibold',
    
    // Prose (pour les reports)
    'prose-report': 'prose prose-indigo prose-sm sm:prose-base max-w-none',
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
          'color': '#4f46e5',
          'text-decoration': 'none',
          '&:hover': {
            'text-decoration': 'underline',
          },
        },
        'blockquote': {
          'border-left-color': '#6366f1',
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
  safelist: [
    // Statuts dynamiques
    'badge-available', 'badge-claimed', 'badge-adopted', 'badge-forked', 'badge-pc',
    // Icônes fréquentes
    'i-lucide-user', 'i-lucide-users', 'i-lucide-book-open', 'i-lucide-link',
    'i-lucide-git-merge', 'i-lucide-git-branch', 'i-lucide-sparkles',
    'i-lucide-plus', 'i-lucide-edit', 'i-lucide-trash', 'i-lucide-check',
    'i-lucide-x', 'i-lucide-search', 'i-lucide-menu', 'i-lucide-bell',
  ],
})
