---
paths:
  - "frontend/src/**/*.js"
  - "templates/**/*.html"
---

# Alpine.js — cycle de vie composants

## Timers et listeners

- Tout `setInterval` / `setTimeout` doit stocker son handle dans une propriété du composant
- Tout handle doit être nettoyé dans `destroy()` via `clearInterval` / `clearTimeout`
  **Why:** Alpine ne nettoie pas automatiquement à la navigation HTMX, le timer fuit et continue à émettre des requêtes en arrière-plan
- Un seul timer par responsabilité — `interval` pour le polling, `heartbeatInterval` pour le keepalive, etc.
- Pattern correct :
  ```javascript
  Alpine.data('component', () => ({
    interval: null,
    init() { this.interval = setInterval(() => this.poll(), 15000) },
    destroy() { clearInterval(this.interval) },
  }))
  ```

## Données injectées depuis Django

- Ne jamais interpoler `{{ var }}` dans une string JS Alpine — XSS garanti
- Passer les valeurs via `data-*` + `$el.dataset.x` dans le handler
- Toujours `|escapejs` sur les valeurs injectées
- Exception whitelistée : une valeur validée serveur à N choix fixes peut être injectée via `data-*` + `x-init` :
  ```html
  <div data-initial-mode="{{ mode }}" x-data="{ mode: '' }" x-init="mode = $el.dataset.initialMode">
  ```

## Composant `tabs` et HTMX

- Le composant `Alpine.data('tabs')` fait du show/hide client-side sur des éléments déjà dans le DOM
- Il est **incompatible** avec HTMX content swap : `activeTab` ne se synchronise pas avec le contenu chargé par HTMX
- Pour un toggle de mode qui charge des partials serveur différents : utiliser `x-data="{ mode: '' }"` inline + `hx-get` sur les boutons
