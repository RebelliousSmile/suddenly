# Decision: Transfert de signalement cross-instance post-MVP

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-017        |
| Date    | 2026-03-05     |
| Feature | Modération     |
| Status  | Accepted       |

## Context

US-27 mentionne que l'admin peut transférer un signalement à l'instance distante via Flag activity. Cela nécessite un protocole spécifique entre instances.

## Decision

Le transfert de signalement cross-instance (Flag AP) est reporté post-MVP. Au MVP, les signalements sont locaux à l'instance.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Flag AP dès le MVP | Modération fédérée complète | Protocole complexe, peu d'instances au lancement | Effort disproportionné |
| Pas de signalement | Simplicité | Pas de modération | Inacceptable |

## Consequences

- Au MVP, un signalement de contenu distant ne remonte qu'à l'admin local
- L'admin local peut bloquer/limiter l'instance distante (US-26) mais pas transférer le cas
- Flag activity ajouté quand la fédération de modération devient nécessaire
