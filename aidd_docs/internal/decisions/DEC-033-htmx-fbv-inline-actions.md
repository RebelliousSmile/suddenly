---
name: DEC-033-htmx-fbv-inline-actions
description: Pattern HTMX pour actions inline dans les FBVs Django (3 templates + détection safe)
type: decision
---

# Decision: Pattern HTMX pour actions inline dans les FBVs

| Field   | Value                        |
| ------- | ---------------------------- |
| ID      | DEC-033                      |
| Date    | 2026-05-01                   |
| Feature | HTMX / Characters / US-14    |
| Status  | Accepted                     |

## Context

US-14 introduit des actions inline (accepter/refuser une demande de lien) depuis le dashboard GM via HTMX. Il fallait un pattern cohérent pour gérer les 3 états d'un item : carte initiale → formulaire inline → état résolu ; et éviter les erreurs mypy dues à l'absence de stubs django-htmx.

## Decision

1. **Détection HTMX** : toujours `getattr(request, "htmx", False)` dans les FBVs — `request.htmx` lève `attr-defined` mypy sans stubs.
2. **3 templates par action inline** : `_X_form.html` (formulaire), `_X_resolved.html` (post-action), `_X_card_fragment.html` (restauration via cancel).
3. `hx-target="#item-{{ id }}"` + `hx-swap="outerHTML"` sur chaque déclencheur ; endpoint GET dédié (`card_partial`) pour la restauration.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| `request.htmx` direct | Plus lisible | Erreur mypy sans stubs | Incompatible avec typecheck strict |
| Alpine.js x-show | Pas de requête serveur | État client diverge | SSR préféré pour les données serveur |
| Un seul template avec conditions | Moins de fichiers | Logique conditionnelle complexe | DRY + lisibilité favorisent la séparation |

## Consequences

- ✅ Typecheck strict préservé (`make check` passe)
- ✅ Pattern réutilisable pour toute action inline future (modération, résolution, etc.)
- ✅ Cancel sans re-fetch du modèle complet (endpoint léger `card_partial`)
- ⚠️ 3 fichiers par action inline — acceptable car chaque template a un rôle unique
