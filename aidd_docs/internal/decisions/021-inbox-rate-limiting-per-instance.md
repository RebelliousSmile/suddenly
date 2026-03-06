# Decision: Rate limiting inbox par instance

| Field   | Value                      |
| ------- | -------------------------- |
| ID      | DEC-021                    |
| Date    | 2026-03-06                 |
| Feature | ActivityPub                |
| Status  | Accepted                   |

## Context

Les endpoints inbox ActivityPub sont publics et sans authentification (par design AP). Un acteur malveillant peut saturer les workers Django avec des requêtes signées ou non.

## Decision

Rate limiting par domaine d'instance distante via `django-ratelimit` :
- Instances connues (dans `FederatedServer`) : 100 req/min
- Instances inconnues : 10 req/min
- Vérification avant `verify_signature()` pour économiser les ressources

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| --- | --- | --- | --- |
| Rate limiting global (par IP) | Simple | Ne distingue pas les instances, CDN/proxy masquent les IPs | Trop grossier pour la fédération |
| Middleware Django custom | Contrôle total | Réinventer la roue | django-ratelimit est mature et testé |

## Consequences

- Protection DoS sur les endpoints inbox
- Instances de confiance (fédérées) ont un seuil 10x plus élevé
- django-ratelimit ajouté aux dépendances federation extras
- Utilise le cache Django (DB fallback si pas de Redis)
