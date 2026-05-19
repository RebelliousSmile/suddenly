---
name: backend-communication
description: Frontend-backend communication patterns for Suddenly
argument-hint: N/A
scope: frontend
---

# Communication between backend and frontend

- **API definition**: `/api/schema/` (OpenAPI), Swagger at `/api/docs/`
- **Services**: HTMX for server-rendered partials, DRF REST API for data ops, Django allauth for auth
- **Request Types**: HTMX GET/POST for partials, JSON REST for data, `application/activity+json` for ActivityPub
- **Entities**: `suddenly/{app}/models.py`, serializers in `suddenly/{app}/views.py` or `serializers.py`
- **Data Flow**: Browser → HTMX partial → Django view → Service layer → ORM → PostgreSQL
- **Error Handling**: Django form errors in HTML partials, DRF `{detail}` or `{field: [errors]}` JSON
- **Validation**: Form validation in `*_forms.py`, DRF serializer validation, model `clean()` methods

### Data Flow

```mermaid
---
title: HTMX request flow
---
sequenceDiagram
    participant Browser
    participant HTMX
    participant DjangoView["Django View"]
    participant Service["Service Layer"]
    participant ORM
    participant DB["PostgreSQL"]

    Browser->>HTMX: hx-post / hx-get
    HTMX->>DjangoView: HTTP request
    DjangoView->>Service: business logic call
    Service->>ORM: queryset / save
    ORM->>DB: SQL
    DB-->>ORM: rows
    ORM-->>Service: model instances
    Service-->>DjangoView: result
    DjangoView-->>HTMX: partial HTML response
    HTMX-->>Browser: swap target
```
