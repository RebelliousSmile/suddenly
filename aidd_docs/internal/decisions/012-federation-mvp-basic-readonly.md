# Decision: Fédération MVP basique read-only

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-012        |
| Date    | 2026-03-05     |
| Feature | Fédération     |
| Status  | Accepted       |

## Context

Le projet est fédéré par design (ActivityPub). Il faut définir le périmètre de fédération au MVP vs ce qui est reporté.

## Decision

MVP = Follow + CRs et Citations visibles depuis Mastodon (read-only). Les Offer (Claim/Adopt/Fork) cross-instance sont reportées post-MVP.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Pas de fédération au MVP | Plus simple | Perd l'identité du projet | Le réseau fédéré est le coeur du pitch |
| Fédération complète | Feature-complete | Trop ambitieux pour le MVP | Liens cross-instance = complexité énorme |

## Consequences

- Acteurs AP : User (Person), Character (Person) — suivables
- Objets AP : Report (Article), Quote (Note) — fédérés
- Game (Group) — pas d'activités spécifiques au MVP
- HTTP Signatures nécessaires dès le MVP
- Les liens restent mono-instance au MVP
