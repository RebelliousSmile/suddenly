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

## GenericForeignKey in .create()

- Never pass `gfk_field=<instance>` to `.create()` — silently ignored by Django manager
- Always set underlying fields explicitly: `target_content_type=ContentType.objects.get_for_model(X), target_object_id=instance.pk`

## Shared queryset builders

- Extract `build_*_queryset` to `<app>/services.py` as soon as 2+ callers need it
- Signature must take domain parameters (`q`, `status`, `system`, `tag`, `user`) — never `HttpRequest`
- Views extract params from `request.GET` then call the service
- Never import a builder from another view — services are the only cross-app boundary
  **Why:** views importing views creates an inverted dependency graph and prevents independent testing of the queryset logic.

## Shared publication service — `publish_report`

- All publication paths (API, `report_create`, `report_edit`, `report_compose`) call `publish_report(report, user)` in `games/services.py`
- Wrap `publish_report` in `@transaction.atomic` — NPC creation + CharacterAppearance must be coherent
- Never inline NPC-from-cast or status-update logic in a view
  **Why:** prior duplication caused `report_compose` to silently skip NPC creation; centralization is the only audit-able fix.
