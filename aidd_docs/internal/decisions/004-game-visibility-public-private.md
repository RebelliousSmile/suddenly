# Decision: Parties publiques ou privées

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-004        |
| Date    | 2026-03-05     |
| Feature | Parties        |
| Status  | Accepted       |

## Context

US-02 décrit les parties comme publiques et suivables. Certains joueurs peuvent vouloir documenter des parties sans les rendre publiques (brouillons, parties sensibles, tests).

## Decision

Les parties peuvent être publiques ou privées au choix du joueur. Une partie privée n'est visible que par son créateur et n'est pas fédérée.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Toutes publiques | Simplicité | Pas de brouillon, pas de vie privée | Trop restrictif |
| Public/Unlisted/Private | Flexibilité | Complexité UI, 3 niveaux à expliquer | Over-engineering au MVP |

## Consequences

- Champ `is_public` déjà présent dans le modèle Game
- Les PNJ d'une partie privée ne sont pas visibles pour adoption
- Une partie peut passer de privée à publique (mais pas l'inverse si des liens existent)
