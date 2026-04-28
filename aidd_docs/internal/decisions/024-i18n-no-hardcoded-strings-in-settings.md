# Decision: i18n — pas de chaînes en dur dans les settings

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-024        |
| Date    | 2026-04-28     |
| Feature | i18n           |
| Status  | Accepted       |

## Context

`SITE_DESCRIPTION` était définie en français dans `base.py`. Le context processor retournait cette valeur directement, bypassing le système de traduction. Les utilisateurs anglophones voyaient la description en français quelle que soit leur langue choisie.

Deuxième piège : `str(_("..."))` dans un context processor évalue la traduction au moment de l'import du module (avant que la langue de la requête soit connue), pas à la requête.

## Decision

Les settings Python ne doivent jamais contenir de chaînes UI dans une langue spécifique. Utiliser `None` comme valeur par défaut et `gettext_lazy` dans le code appelant, ou omettre la valeur et laisser le context processor gérer le fallback lazy.

Pattern correct dans un context processor :
```python
"SITE_DESCRIPTION": getattr(settings, "SITE_DESCRIPTION", None) or _("Federated shared fiction network"),
```

(`_` importé depuis `django.utils.translation.gettext_lazy` — évaluation à la requête, pas à l'import)

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| `str(_(...))` dans le context processor | Simple | Évalue à l'import, pas à la requête | Bug silencieux : langue figée au démarrage |
| Chaîne en dur dans la langue principale | Simple | Non traduisible | Exclut les utilisateurs d'autres langues |

## Consequences

- Toute chaîne UI configurable dans les settings doit être `None` ou une `_StrPromise` (lazy)
- Le type de retour du context processor devient `dict[str, object]` (pas `dict[str, str]`)
- Les traductions reflètent correctement la langue active de chaque requête
