# Decision: Explorer et Jouer hors du bloc auth dans la nav

| Field   | Value                    |
| ------- | ------------------------ |
| ID      | DEC-029                  |
| Date    | 2026-04-29               |
| Feature | Explorer nav refactor    |
| Status  | Accepted                 |

## Context

La navigation groupait tous les liens sous `{% if user.is_authenticated %}`, rendant la découverte de contenu public inaccessible aux visiteurs non connectés. Explorer (personnages/parties publics) et Jouer (fil fédéré) sont des pages publiques par nature.

## Decision

Les liens Explorer (`/explorer/`) et Jouer (`/feed/`) sont placés hors du bloc auth dans la nav desktop et mobile. Les liens de gestion (profil, parties, déconnexion) restent dans le bloc auth.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Tout garder dans le bloc auth | Simplicité template | Empêche toute découverte sans compte | Contraire à l'objectif réseau fédéré ouvert |

## Consequences

- Les vues `/explorer/` et `/feed/` doivent gérer `request.user` anonyme (déjà le cas via `AnonymousUser`)
- `build_game_queryset` reçoit `user: AbstractBaseUser | AnonymousUser` pour filtrer les parties privées
