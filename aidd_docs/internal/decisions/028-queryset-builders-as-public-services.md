# Decision: build_*_queryset en services publics, pas helpers privés dans les vues

| Field   | Value                    |
| ------- | ------------------------ |
| ID      | DEC-028                  |
| Date    | 2026-04-29               |
| Feature | Explorer nav refactor    |
| Status  | Accepted                 |

## Context

Les helpers `_build_character_queryset` et `_build_game_queryset` étaient définis comme fonctions privées dans `characters/front_views.py` et `games/front_views.py`. La nouvelle page `/explorer/` (dans `core/views.py`) avait besoin des mêmes querysets, rendant le partage impossible sans duplication.

## Decision

Dès qu'un queryset builder est utilisé par 2 appelants ou plus, il est extrait en service public (`build_*_queryset`) dans `<app>/services.py`. La signature reçoit des paramètres domaine explicites (`q`, `status`, `system`, `tag`, `user`) — jamais `HttpRequest`.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Garder en `front_views.py` et importer cross-app | Simple | Couplage vues → vues, viole la règle services | Anti-pattern détecté par code review |
| Dupliquer dans `core/views.py` | Isolation | Divergence garantie | Viole DRY (règle `07-dry-refactor.md`) |

## Consequences

- `build_character_queryset` dans `characters/services.py`, `build_game_queryset` dans `games/services.py`
- Les vues extraient les paramètres de `request.GET` avant d'appeler le service
- Le service est indépendamment testable sans requête HTTP
