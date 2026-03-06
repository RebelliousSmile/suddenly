# Decision: Redis optionnel avec fallback DB cache

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-022        |
| Date    | 2026-03-06     |
| Feature | Infrastructure |
| Status  | Accepted       |

## Context

Certains hébergeurs (ex. Alwaysdata) ne proposent pas Redis. Le projet doit pouvoir tourner sans lui, quelle que soit l'infrastructure choisie par l'opérateur d'instance.

## Decision

Si `REDIS_URL` est absent, le projet bascule automatiquement sur DB cache et `CELERY_TASK_ALWAYS_EAGER=True`. Ce comportement est géré dans `config/settings/production.py` sans configuration supplémentaire.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Redis obligatoire | Performances uniformes | Exclut certains hébergeurs | Trop restrictif pour un projet communautaire |
| Fichier cache | Simple | Non distribué, non fiable | Pas adapté à la prod |

## Consequences

- Les instances sans Redis ont des performances de cache légèrement inférieures
- Les tâches Celery s'exécutent en synchrone (latence légère sur les activités AP)
- Les crons remplacent le worker Celery pour les tâches périodiques
