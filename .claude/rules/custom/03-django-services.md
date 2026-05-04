---
paths:
  - "suddenly/**/services.py"
---

# Django services layer

- Services contain all business logic — views and models are thin
- Service methods receive domain objects, not request objects
- Each service method does one thing and is independently testable
- Wrap multi-step mutations in `transaction.atomic()`
- Services call other services, never import views

## Atomic check-then-create (DEC-035)

- Lock the **parent row** as transaction anchor, not the dependent queryset
- `select_for_update()` on an empty queryset locks nothing in READ COMMITTED
- Pattern: `parent = Model.objects.select_for_update().get(pk=pk)` then check + create

## GenericForeignKey in .create() (DEC-036)

- Never pass `gfk_field=<instance>` to `.create()` — silently ignored by Django manager
- Always set underlying fields explicitly: `target_content_type=ContentType.objects.get_for_model(X), target_object_id=instance.pk`
