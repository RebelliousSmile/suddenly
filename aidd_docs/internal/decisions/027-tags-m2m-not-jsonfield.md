# Decision: tags en ManyToManyField vers core.Tag, pas JSONField

| Field   | Value          |
| ------- | -------------- |
| ID      | DEC-027        |
| Date    | 2026-04-29     |
| Feature | Tags           |
| Status  | Accepted       |

## Context

`Character.tags` était stocké comme `JSONField(default=list)` — liste de chaînes brutes. `Report.tags` utilisait déjà un `ManyToManyField → core.Tag`. L'incohérence empêchait le filtrage uniforme et la découverte cross-instance par hashtag.

## Decision

Tous les modèles exposant des tags (`Character`, `Game`, `Report`) utilisent `ManyToManyField("core.Tag", blank=True)`. Le modèle `core.Tag` (name unique) est la source de vérité. Les vues éditent les tags via `obj.tags.set(tag_objects)` après `obj.save()`.

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| Garder JSONField | Pas de migration | Non requêtable via ORM, pas de déduplication | Incompatible avec découverte AP |
| `django-taggit` | Fonctionnalité riche | Dépendance externe | `core.Tag` suffit, on garde le contrôle |

## Consequences

- Migration en 3 étapes obligatoires pour JSONField → M2M : add M2M (0007) → data migration (0008) → remove JSONField (0009)
- `update_fields` dans `save()` ne doit jamais inclure un champ M2M
- `obj.tags.set()` doit être appelé **après** `obj.save()` (PK requis)
- Template : `{% if obj.pk %}{{ obj.tags.all|join:', ' }}{% endif %}` pour éviter ValueError sur instance non sauvegardée
