# Decision: Détection d'instances Suddenly via NodeInfo

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-013        |
| Date    | 2026-03-05     |
| Feature | Fédération     |
| Status  | Accepted       |

## Context

US-24 stipule que les activités Suddenly-only (Offer) ne doivent pas être envoyées aux instances non-Suddenly. Il faut un mécanisme de détection.

## Decision

Utiliser NodeInfo pour identifier les instances Suddenly. Le champ `software.name` = "suddenly" permet de distinguer les instances compatibles.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Header custom dans les requêtes | Léger | Non standard, fragile | Pas interopérable |
| Tester les endpoints Suddenly | Pas de standard requis | Lent, requêtes inutiles | Pas fiable |

## Consequences

- Endpoint `/.well-known/nodeinfo` implémenté dès le MVP
- FederatedServer stocke le type d'instance détecté
- Les activités Suddenly-only sont filtrées côté outbox
- Compatible avec le protocole NodeInfo existant (Mastodon, BookWyrm, etc.)
