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

// Password strength meter
Alpine.data('passwordStrength', (fieldId) => ({
  strength: 0,
  label: '',

  init() {
    const field = document.getElementById(fieldId)
    if (!field) return
    field.addEventListener('input', () => this.evaluate(field.value))
  },

  evaluate(password) {
    if (!password) {
      this.strength = 0
      this.label = ''
      return
    }

    let score = 0
    if (password.length >= 8) score++
    if (password.length >= 12) score++
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++
    if (/\d/.test(password)) score++
    if (/[^a-zA-Z0-9]/.test(password)) score++

    this.strength = Math.min(Math.max(Math.ceil(score * 4 / 5), 1), 4)

    const labels = {
      1: 'Faible — ajoutez des majuscules, chiffres ou symboles',
      2: 'Moyen — ajoutez de la variété',
      3: 'Bon',
      4: 'Excellent',
    }
    this.label = labels[this.strength]
  },
}))

// Autosave indicator for report editor
Alpine.data('autosave', (saveUrl) => ({
  status: 'saved',  // 'saved' | 'saving' | 'unsaved' | 'error'
  timer: null,

  init() {
    this.$watch('status', () => {})
  },

  markDirty() {
    this.status = 'unsaved'
    clearTimeout(this.timer)
    this.timer = setTimeout(() => this.save(), 3000)
  },

  async save() {
    if (this.status === 'saving') return
    this.status = 'saving'

    try {
      const form = this.$el.closest('form')
      const formData = new FormData(form)
      formData.set('status', 'draft')

      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
      const response = await fetch(saveUrl, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken },
        body: formData,
      })

      this.status = response.ok ? 'saved' : 'error'
    } catch {
      this.status = 'error'
    }
  },

  get icon() {
    return {
      saved: 'i-lucide-cloud',
      saving: 'i-lucide-loader-2 animate-spin',
      unsaved: 'i-lucide-cloud-off',
      error: 'i-lucide-alert-triangle text-red-500',
    }[this.status]
  },

  get text() {
    return {
      saved: 'Sauvegardé',
      saving: 'Sauvegarde...',
      unsaved: 'Non sauvegardé',
      error: 'Erreur de sauvegarde',
    }[this.status]
  },
}))

// Presence indicator for SharedSequence (polling-based)
Alpine.data('presence', (sequenceId, currentUserId) => ({
  participants: [],
  interval: null,

  init() {
    this.poll()
    this.interval = setInterval(() => this.poll(), 15000)
    // Signal own presence
    this.heartbeat()
    setInterval(() => this.heartbeat(), 10000)
  },

  destroy() {
    clearInterval(this.interval)
  },

  async poll() {
    try {
      const response = await fetch(`/api/sequences/${sequenceId}/presence/`)
      if (response.ok) {
        this.participants = await response.json()
      }
    } catch {
      // Silently fail — presence is non-critical
    }
  },

  async heartbeat() {
    try {
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
      await fetch(`/api/sequences/${sequenceId}/presence/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_id: currentUserId }),
      })
    } catch {
      // Silently fail
    }
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
