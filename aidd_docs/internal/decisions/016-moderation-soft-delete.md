# Decision: Soft delete pour le contenu modéré

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-016        |
| Date    | 2026-03-05     |
| Feature | Modération     |
| Status  | Accepted       |

## Context

US-25 décrit la suppression de contenu par un admin. Il faut décider si la suppression est réversible.

## Decision

Soft delete : le contenu modéré est masqué (flag `is_deleted` ou `deleted_at`) mais récupérable par l'admin. L'auteur est notifié avec la raison.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Hard delete | Irréversible, propre | Pas de recours en cas d'erreur | Trop destructif |
| Masquage temporaire avec appel | Process lourd | Complexité workflow | Over-engineering au MVP |

## Consequences

- Tous les modèles avec contenu utilisateur ont un champ `deleted_at`
- Le contenu soft-deleted est exclu des requêtes par défaut (manager custom)
- L'admin peut restaurer du contenu dans le panneau d'administration
- Un Delete AP est émis pour les instances distantes
