# Task [CLAUDE.md — omissions vs memory bank]

Inconsistency detected during an Ada session on 2026-03-06.

## Files involved

- [x] `CLAUDE.md` — listait le frontend comme "Django + HTMX + Tailwind" sans mentionner Alpine.js
- [x] `aidd_docs/memory/ARCHITECTURE.md` — mentionne explicitement Alpine.js dans le frontend

- [x] `CLAUDE.md` — listait 6 types de commits : feat, fix, refactor, docs, test, chore
- [x] `aidd_docs/memory/VCS.md` — liste 10 types de commits, dont style, ci, revert, perf absents de CLAUDE.md

## Fixes applied

- [x] Alpine.js confirme dans `frontend/package.json` (alpinejs ^3.14.0) et `frontend/src/main.js`
- [x] Frontend corrige : "Django + HTMX + Alpine.js + UnoCSS | SSR + Vite build" (aussi corrige Tailwind → UnoCSS)
- [x] 4 types de commits ajoutes (style, ci, revert, perf)
- [x] CLAUDE.md est gitignored — corrections appliquees localement
