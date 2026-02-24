// =================================================================
// Suddenly - Main JavaScript Entry Point
// =================================================================

// UnoCSS - génère les styles
import 'virtual:uno.css'

// HTMX - interactions serveur
import htmx from 'htmx.org'
window.htmx = htmx

// Alpine.js - réactivité locale
import Alpine from 'alpinejs'
window.Alpine = Alpine

// =================================================================
// Configuration HTMX
// =================================================================

// CSRF token pour Django
document.body.addEventListener('htmx:configRequest', (event) => {
  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
    || document.cookie.match(/csrftoken=([^;]+)/)?.[1]
  
  if (csrfToken) {
    event.detail.headers['X-CSRFToken'] = csrfToken
  }
})

// Indicateur de chargement global
document.body.addEventListener('htmx:beforeRequest', () => {
  document.body.classList.add('htmx-request')
})

document.body.addEventListener('htmx:afterRequest', () => {
  document.body.classList.remove('htmx-request')
})

// Gestion des erreurs HTMX
document.body.addEventListener('htmx:responseError', (event) => {
  console.error('HTMX Error:', event.detail)
  
  // Afficher une notification d'erreur
  const message = event.detail.xhr.status === 403
    ? 'Action non autorisée'
    : 'Une erreur est survenue'
  
  window.dispatchEvent(new CustomEvent('notify', {
    detail: { message, type: 'error' }
  }))
})

// =================================================================
// Composants Alpine.js
// =================================================================

// Dropdown/Menu
Alpine.data('dropdown', () => ({
  open: false,
  toggle() {
    this.open = !this.open
  },
  close() {
    this.open = false
  },
}))

// Modal
Alpine.data('modal', () => ({
  open: false,
  show() {
    this.open = true
    document.body.style.overflow = 'hidden'
  },
  hide() {
    this.open = false
    document.body.style.overflow = ''
  },
}))

// Notifications/Toast
Alpine.data('notifications', () => ({
  items: [],
  
  init() {
    window.addEventListener('notify', (e) => {
      this.add(e.detail)
    })
  },
  
  add({ message, type = 'info', duration = 5000 }) {
    const id = Date.now()
    this.items.push({ id, message, type })
    
    if (duration > 0) {
      setTimeout(() => this.remove(id), duration)
    }
  },
  
  remove(id) {
    this.items = this.items.filter(item => item.id !== id)
  },
}))

// Mention autocomplete (pour l'éditeur de reports)
Alpine.data('mentionInput', (initialValue = '') => ({
  content: initialValue,
  suggestions: [],
  showSuggestions: false,
  selectedIndex: 0,
  
  async search(query) {
    if (query.length < 2) {
      this.suggestions = []
      return
    }
    
    try {
      const response = await fetch(`/api/characters/search/?q=${encodeURIComponent(query)}`)
      this.suggestions = await response.json()
      this.showSuggestions = this.suggestions.length > 0
      this.selectedIndex = 0
    } catch (e) {
      console.error('Search error:', e)
    }
  },
  
  selectSuggestion(suggestion) {
    // Insérer la mention
    this.content = this.content.replace(/@\w*$/, `@${suggestion.name} `)
    this.showSuggestions = false
  },
  
  onKeydown(event) {
    if (!this.showSuggestions) return
    
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault()
        this.selectedIndex = Math.min(this.selectedIndex + 1, this.suggestions.length - 1)
        break
      case 'ArrowUp':
        event.preventDefault()
        this.selectedIndex = Math.max(this.selectedIndex - 1, 0)
        break
      case 'Enter':
        event.preventDefault()
        if (this.suggestions[this.selectedIndex]) {
          this.selectSuggestion(this.suggestions[this.selectedIndex])
        }
        break
      case 'Escape':
        this.showSuggestions = false
        break
    }
  },
}))

// Tabs
Alpine.data('tabs', (defaultTab = '') => ({
  activeTab: defaultTab,
  
  init() {
    if (!this.activeTab) {
      this.activeTab = this.$el.querySelector('[data-tab]')?.dataset.tab || ''
    }
  },
  
  isActive(tab) {
    return this.activeTab === tab
  },
  
  select(tab) {
    this.activeTab = tab
  },
}))

// Character status toggle
Alpine.data('characterStatus', (status) => ({
  status,
  loading: false,
  
  get statusLabel() {
    const labels = {
      npc: 'PNJ disponible',
      pc: 'PJ',
      claimed: 'Réclamé',
      adopted: 'Adopté',
      forked: 'Forké',
    }
    return labels[this.status] || this.status
  },
  
  get statusClass() {
    return `badge-${this.status === 'npc' ? 'available' : this.status}`
  },
}))

// =================================================================
// Initialisation
// =================================================================

// Démarrer Alpine
Alpine.start()

// Log de debug en dev
if (import.meta.env.DEV) {
  console.log('🎭 Suddenly frontend loaded')
  console.log('   HTMX:', htmx.version)
  console.log('   Alpine:', Alpine.version)
}
