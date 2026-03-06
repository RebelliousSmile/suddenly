# Task [characters/models.py n'hérite pas de BaseModel]

Inconsistency detected during an Ada session on 2026-03-06.

## Files involved

- [ ] `suddenly/core/models.py` — définit `BaseModel` (UUID PK, timestamps) comme modèle abstrait de base que tous les modèles doivent hériter
- [ ] `.claude/rules/custom/03-django-models.md` — stipule "All models inherit from `core.models.BaseModel`"
- [ ] `suddenly/characters/models.py` — tous les modèles (`Character`, `Quote`, `CharacterAppearance`, `LinkRequest`, `CharacterLink`, `SharedSequence`, `Follow`) héritent directement de `models.Model` au lieu de `BaseModel`, et redéfinissent manuellement `id`, `created_at`, `updated_at`

## To fix

- [ ] Determine which source is correct (la règle `03-django-models.md` semble être la référence)
- [ ] Mettre à jour `characters/models.py` pour que tous les modèles héritent de `BaseModel` et supprimer les champs redondants (`id`, `created_at`, `updated_at`)
- [ ] Vérifier si d'autres modèles du projet ont le même problème (`games/models.py`, `users/models.py`, `activitypub/models.py`)
- [ ] Vérifier les migrations associées si des changements de schéma sont nécessaires
