# Decision: Citations éphémères à durée fixe 24h

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-006        |
| Date    | 2026-03-05     |
| Feature | Citations      |
| Status  | Accepted       |

## Context

Le brief définit une visibilité EPHEMERAL qui "disparaît après la session". Suddenly n'a pas de concept de session — il faut un déclencheur concret.

## Decision

EPHEMERAL = suppression automatique après 24h. Type story Instagram. Non fédérée.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Supprimer EPHEMERAL | Simplicité | Perte d'une feature fun | Valeur sociale des moments spontanés |
| Fermeture manuelle | Contrôle total | Le joueur oublie de fermer | Données fantômes |
| Liée au brouillon du CR | Logique | Trop couplé au workflow de rédaction | Cas d'usage trop restreint |

## Consequences

- Tâche planifiée (cron/Celery) pour purger les citations expirées
- EPHEMERAL n'est jamais fédérée (durée trop courte)
- UI : indicateur visuel du temps restant sur la citation
