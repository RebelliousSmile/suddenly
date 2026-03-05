# Decision: Fils d'actualité personnel + local au MVP

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-005        |
| Date    | 2026-03-05     |
| Feature | Découverte     |
| Status  | Accepted       |

## Context

Les US ne définissent pas comment un nouveau joueur découvre du contenu. Le modèle fédéré classique propose 3 fils (personnel, local, global). Le fil global nécessite une fédération active.

## Decision

MVP = fil personnel (CRs des joueurs/parties suivis) + fil local (contenu public de l'instance). Fil global reporté post-MVP quand la fédération est mature.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| 3 fils dès le MVP | Expérience complète | Fil global vide sans fédération active | Fausse promesse au lancement |
| Recherche uniquement | Simple | Pas de découverte passive | Trop aride pour un réseau social |

## Consequences

- Page d'accueil connectée = fil personnel
- Page "Local" = tous les CRs publics de l'instance
- Les nouveaux joueurs voient du contenu dès le fil local
- Fil global ajouté quand plusieurs instances existent
