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
