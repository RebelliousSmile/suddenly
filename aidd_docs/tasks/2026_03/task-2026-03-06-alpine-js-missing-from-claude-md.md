# Task [Alpine.js absent du CLAUDE.md]

Inconsistency detected during an Ada session on 2026-03-06.

## Files involved

- [ ] `aidd_docs/memory/ARCHITECTURE.md` — décrit le frontend comme "HTMX + Alpine.js + Tailwind CSS" avec un bundle estimé à ~32KB incluant Alpine.js (8KB)
- [ ] `CLAUDE.md` — décrit la stack frontend comme "Django + HTMX + Tailwind" sans mentionner Alpine.js

## To fix

- [ ] Determine which source is correct (Alpine.js est-il réellement utilisé dans le projet ?)
- [ ] Mettre à jour `CLAUDE.md` pour inclure Alpine.js si c'est effectivement dans la stack
- [ ] Vérifier les templates HTML pour confirmer la présence ou l'absence d'Alpine.js
