# Decision: InstanceSettings singleton pour la configuration d'instance

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-026        |
| Date    | 2026-04-29     |
| Feature | GMH admin panel |
| Status  | Accepted       |

## Context

La configuration d'instance (nom, description, langue, inscriptions ouvertes) était stockée dans les settings Django (variables d'environnement). Les modifier nécessitait un redéploiement et ne permettait pas de déléguer la gestion à un admin non-technique.

## Decision

Modèle singleton `InstanceSettings` (pk=1 fixe) dans `core.models`. Méthode de classe `InstanceSettings.get()` retourne la ligne unique en la créant si absente. Propagée au contexte template via `context_processors`, à la langue via `InstanceLanguageMiddleware`, et aux métadonnées NodeInfo.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Variables d'environnement uniquement | Simple, 12-factor | Redéploiement requis, pas d'UI admin | Frein pour petites instances |
| `django-constance` | Clé-valeur flexible | Dépendance externe, typage faible | Over-engineering, on contrôle le schéma |

## Consequences

- `InstanceSettings.get()` à utiliser partout — jamais `InstanceSettings.objects.first()`
- Les accès en migration ou au démarrage wrappés dans `try/except OperationalError, ProgrammingError` (table peut ne pas exister)
- `SITE_NAME` et `SITE_DESCRIPTION` dans `settings.py` deviennent des fallbacks optionnels
