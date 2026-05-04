---
name: DEC-036-genericforeignkey-explicit-fields
description: Toujours utiliser les champs sous-jacents pour créer un objet avec GenericForeignKey
type: decision
---

# Decision: GenericForeignKey — champs sous-jacents dans .create()

| Field   | Value                     |
| ------- | ------------------------- |
| ID      | DEC-036                   |
| Date    | 2026-05-04                |
| Feature | Notifications             |
| Status  | Accepted                  |

## Context

Le modèle `Notification` utilise un `GenericForeignKey` (`target`) adossé à `target_content_type` (ForeignKey) et `target_object_id` (UUIDField). Passer `target=<instance>` dans `Notification.objects.create()` est silencieusement ignoré par Django — le GFK n'est pas un vrai champ DB, son descripteur n'est pas invoqué par le manager `create()`.

## Decision

Toujours renseigner les champs sous-jacents explicitement dans `.create()` :

```python
from django.contrib.contenttypes.models import ContentType

Notification.objects.create(
    recipient=target_character.creator,
    type=NotificationType.LINK_REQUEST,
    actor=next_queued.requester,
    target_content_type=ContentType.objects.get_for_model(LinkRequest),
    target_object_id=next_queued.pk,
    message=f"...",
)
```

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| `target=<instance>` dans `.create()` | Lisible | Silencieusement ignoré, `target` reste NULL en DB | Bug invisible, données corrompues |
| Assigner après `create()` via `obj.target = instance; obj.save()` | Fonctionne | Deux requêtes DB | Moins efficace sans avantage |

## Consequences

- Toute création de `Notification` doit passer par `target_content_type` + `target_object_id`
- Règle applicable à tout modèle Django utilisant `GenericForeignKey`
