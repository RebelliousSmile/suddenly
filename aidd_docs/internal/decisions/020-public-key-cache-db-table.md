# Decision: Cache clés publiques AP via table DB

| Field   | Value                      |
| ------- | -------------------------- |
| ID      | DEC-020                    |
| Date    | 2026-03-06                 |
| Feature | ActivityPub                |
| Status  | Accepted                   |

## Context

La vérification de signature HTTP (`verify_signature`) faisait un appel HTTP sortant synchrone à chaque requête entrante pour récupérer la clé publique de l'acteur distant. Risque de DoS par saturation de threads Django.

## Decision

Cache des clés publiques dans une table DB dédiée `PublicKeyCache` (au lieu de Redis) avec mécanisme de retry : si la vérification échoue avec la clé en cache, re-fetch une fois avant rejet.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| --- | --- | --- | --- |
| Cache Django (Redis/DB backend) | Simple, intégré | Pas inspectable, dépend du backend configuré | Moins traçable pour debug fédération |
| Stocker dans User.public_key | Pas de nouvelle table | Couple cache et modèle User, pas de fetched_at | Responsabilités mélangées |

## Consequences

- Toute requête AP vérifiée sans appel HTTP sortant si clé en cache
- Rotation de clé supportée via retry automatique
- Compatible mode minimal (sans Redis)
- Table inspectable en admin pour debug fédération
