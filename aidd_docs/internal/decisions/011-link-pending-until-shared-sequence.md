# Decision: Lien en suspens tant que la SharedSequence n'est pas publiée

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-011        |
| Date    | 2026-03-05     |
| Feature | SharedSequence |
| Status  | Accepted       |

## Context

Le doc mémoire stipule "un lien sans SharedSequence est invalide". Il faut définir l'état du CharacterLink entre l'acceptation de la demande et la publication de la SharedSequence.

## Decision

Le CharacterLink est créé à l'acceptation mais le PNJ ne change de statut qu'à la publication de la SharedSequence. Le lien reste en état "pending completion".

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Changement de statut immédiat | Simple | Lien "officiel" sans contenu narratif | Contraire à la règle métier |
| Pas de CharacterLink avant publication | Cohérent | Pas de trace de l'acceptation | Le joueur ne voit rien entre acceptation et publication |

## Consequences

- CharacterLink a un état intermédiaire (draft/active ou similaire)
- Le PNJ reste en statut NPC jusqu'à publication SS
- La file d'attente est bloquée pendant ce temps (pas de nouvelle demande PENDING)
- Timeout à définir : si la SS n'est jamais publiée, le lien expire
