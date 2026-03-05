# Decision: Statut QUEUED pour LinkRequest

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-007        |
| Date    | 2026-03-05     |
| Feature | Liens          |
| Status  | Accepted       |

## Context

US-15 décrit une file d'attente quand plusieurs joueurs veulent le même PNJ. Le modèle actuel a PENDING/ACCEPTED/REJECTED/CANCELLED mais pas de moyen de distinguer "en cours de traitement" de "en attente dans la file".

## Decision

Ajouter le statut QUEUED à LinkRequest. Seule la première demande est PENDING, les suivantes sont QUEUED. Promotion automatique quand une demande PENDING est refusée.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Bloquer les demandes si PENDING existe | Simple | Perd les propositions alternatives | Frustrant pour les joueurs |
| Tout en PENDING | Pas de nouveau statut | Le GM ne sait pas laquelle traiter en premier | Confusion dans l'UI |

## Consequences

- Statuts LinkRequest : PENDING, QUEUED, ACCEPTED, REJECTED, CANCELLED
- Logique de promotion dans LinkService : QUEUED → PENDING quand la file avance
- Notification au joueur de sa position dans la file
