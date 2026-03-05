# Decision: Timeout des demandes cross-instance à 30 jours

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-014        |
| Date    | 2026-03-05     |
| Feature | Fédération     |
| Status  | Accepted       |

## Context

US-23 définit un timeout de 30 jours pour les demandes cross-instance sans réponse. Il faut décider si c'est fixe ou configurable.

## Decision

30 jours fixe au MVP. Configurable par instance post-MVP.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Pas de timeout | Pas de perte | Demandes fantômes à l'infini | Pollution de la file d'attente |
| 7 jours | Résolution rapide | Trop court pour du jeu asynchrone | Les joueurs de JDR sont lents |

## Consequences

- Tâche Celery quotidienne pour expirer les demandes > 30 jours
- Statut EXPIRED ajouté à LinkRequest
- Notification au demandeur quand sa demande expire
