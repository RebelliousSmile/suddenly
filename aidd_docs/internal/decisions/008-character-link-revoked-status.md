# Decision: Statut REVOKED pour CharacterLink

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-008        |
| Date    | 2026-03-05     |
| Feature | Liens          |
| Status  | Accepted       |

## Context

US-16 permet de révoquer un lien accepté. Avant publication de la SharedSequence, on peut supprimer le lien. Après publication, le contenu co-créé doit rester visible.

## Decision

Ajouter le statut REVOKED à CharacterLink. Avant publication SS : suppression du lien. Après publication SS : lien marqué REVOKED, SharedSequence reste visible avec mention.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Pas de révocation | Simple | Erreurs et abus irréversibles | Inacceptable |
| Suppression dans tous les cas | Propre | Perte de contenu co-créé publié | Injuste pour le co-auteur |

## Consequences

- CharacterLink gagne un champ status (ou is_revoked)
- Le PNJ revient en statut NPC après révocation
- La SharedSequence publiée affiche "lien révoqué" mais reste lisible
- Révocation possible par les deux parties (créateur et demandeur)
