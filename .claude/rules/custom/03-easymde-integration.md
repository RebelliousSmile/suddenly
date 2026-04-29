---
paths:
  - "templates/**/*.html"
  - "frontend/src/**/*.js"
---

# EasyMDE — Règles d'intégration

## Textarea

- Ne jamais mettre `required` sur une textarea gérée par EasyMDE — l'élément est masqué (`display:none`) après init, ce qui bloque la validation HTML5 avec une erreur "not focusable"
- Ne pas ajouter `x-model`, `@input` ou `@keydown` Alpine sur la textarea — EasyMDE prend le contrôle via CodeMirror

## Dropdown de suggestions @mention

- Utiliser `position:fixed` + `cm.cursorCoords(true, 'window')` (coordonnées viewport), pas `position:absolute`
- Appliquer `z-index: 9999` pour passer au-dessus de l'éditeur

## Toolbar

- Le bouton `side-by-side` est désactivé (bugué dans le contexte Alpine) — ne pas le réactiver sans test préalable

## Composant Alpine

- Le composant s'appelle `markdownEditor` — `x-data="markdownEditor('{{ content|escapejs }}')"`
- `init()` est auto-appelé par Alpine ; `this.$el` pointe sur le conteneur `div`
