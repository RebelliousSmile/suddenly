---
name: decision
description: EasyMDE comme éditeur Markdown dans les formulaires de reports
type: decision
---

# Decision: EasyMDE comme éditeur Markdown

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-030        |
| Date    | 2026-04-29     |
| Feature | Report editor  |
| Status  | Accepted       |

## Context

Les formulaires de rédaction de reports nécessitaient un éditeur Markdown avec support du `@mention` autocomplete. Une textarea brute ne permettait pas de positionner précisément le dropdown de suggestions ni de fournir une toolbar Markdown.

## Decision

Utiliser EasyMDE (CodeMirror-based) encapsulé dans un composant Alpine.js `markdownEditor`. L'intégration utilise les événements CodeMirror (`cm.on('change')`, `cm.on('keydown')`) directement.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Textarea brute + `@input` Alpine | Simple, pas de dépendance | Pas de toolbar, difficulté à positionner le dropdown | UX insuffisante |
| TipTap / ProseMirror | Riche, extensible | Lourd, complexité d'intégration Alpine | Surcharge pour le MVP |

## Consequences

- Ne jamais mettre `required` sur la textarea que EasyMDE va masquer — le navigateur ne peut pas focus un élément `display:none`, ce qui bloque la validation HTML5
- Le dropdown de suggestions doit utiliser `position:fixed` avec `cm.cursorCoords(true, 'window')` (coordonnées viewport) et non `position:absolute` (coordonnées relatives au conteneur)
- Le bouton `side-by-side` est désactivé (bugué dans le contexte Alpine — layout cassé)
- `static/dist/` doit inclure le CSS EasyMDE buildé (`easymde/dist/easymde.min.css`)
