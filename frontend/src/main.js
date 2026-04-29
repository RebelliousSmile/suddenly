// =================================================================
// Suddenly - Main JavaScript Entry Point
// =================================================================

// UnoCSS - génère les styles
import 'virtual:uno.css'

// EasyMDE — Markdown editor
import EasyMDE from 'easymde'
import 'easymde/dist/easymde.min.css'

// Base reset
import './base.css'

// EasyMDE theme overrides (light + dark)
import './easymde-theme.css'

// HTMX loading indicator styles
import './htmx-indicator.css'

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

// Theme (dark/light mode)
Alpine.data('theme', () => ({
  isDark: false,
  init() {
    const saved = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    this.isDark = saved ? saved === 'dark' : prefersDark;
    document.documentElement.dataset.theme = this.isDark ? 'dark' : 'light';
  },
  toggle() {
    this.isDark = !this.isDark;
    const theme = this.isDark ? 'dark' : 'light';
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('theme', theme);
  },
}))

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

// Markdown editor with EasyMDE + @mention autocomplete
Alpine.data('markdownEditor', (initialValue = '') => ({
  suggestions: [],
  showSuggestions: false,
  selectedIndex: 0,
  dropdownStyle: { top: '0px', left: '0px' },
  _easyMde: null,
  _mentionStart: -1,

  init() {
    const textarea = this.$el.querySelector('textarea')
    if (!textarea) return

    this._easyMde = new EasyMDE({
      element: textarea,
      initialValue,
      spellChecker: false,
      autosave: { enabled: false },
      toolbar: ['bold', 'italic', 'heading', '|', 'quote', 'unordered-list', 'ordered-list', '|', 'link', '|', 'preview', 'fullscreen'],
    })

    const cm = this._easyMde.codemirror
    cm.on('change', () => this._onCmChange(cm))
    cm.on('keydown', (_cm, event) => this._onKeydown(event))
  },

  _onCmChange(cm) {
    const cursor = cm.getCursor()
    const lineText = cm.getLine(cursor.line)
    const textBeforeCursor = lineText.slice(0, cursor.ch)
    const mentionMatch = textBeforeCursor.match(/@(\w*)$/)

    if (mentionMatch) {
      this._mentionStart = cursor.ch - mentionMatch[0].length
      this._updateDropdownPosition(cm)
      this._search(mentionMatch[1])
    } else {
      this.showSuggestions = false
      this._mentionStart = -1
    }
  },

  _updateDropdownPosition(cm) {
    const coords = cm.cursorCoords(true, 'window')
    this.dropdownStyle = {
      position: 'fixed',
      top: `${coords.bottom + 4}px`,
      left: `${coords.left}px`,
      'z-index': '9999',
    }
  },

  async _search(query) {
    if (query.length < 2) {
      this.suggestions = []
      this.showSuggestions = false
      return
    }
    try {
      const response = await fetch(`/api/characters/search/?q=${encodeURIComponent(query)}`)
      if (!response.ok) return
      this.suggestions = await response.json()
      this.showSuggestions = this.suggestions.length > 0
      this.selectedIndex = 0
    } catch (e) {
      console.error('Mention search error:', e)
    }
  },

  selectSuggestion(suggestion) {
    if (!this._easyMde || this._mentionStart < 0) return
    const cm = this._easyMde.codemirror
    const cursor = cm.getCursor()
    const mention = `@${suggestion.name} `
    cm.replaceRange(mention, { line: cursor.line, ch: this._mentionStart }, cursor)
    this.showSuggestions = false
    this._mentionStart = -1
    cm.focus()
  },

  _onKeydown(event) {
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
      claimed: 'Révélé',
      adopted: 'Adopté',
      forked: 'Dérivé',
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
  _saveVersion: 0,

  init() {},

  markDirty() {
    this.status = 'unsaved'
    this._saveVersion++
    clearTimeout(this.timer)
    this.timer = setTimeout(() => this.save(), 3000)
  },

  async save() {
    const version = this._saveVersion
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

      // Only update status if no newer changes came in during save
      if (version === this._saveVersion) {
        this.status = response.ok ? 'saved' : 'error'
      }
    } catch {
      if (version === this._saveVersion) {
        this.status = 'error'
      }
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
