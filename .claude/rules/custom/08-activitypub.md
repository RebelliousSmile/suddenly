---
paths:
  - "suddenly/activitypub/**"
---

# ActivityPub domain rules

- All outgoing requests signed with HTTP Signatures (RSA-SHA256)
- Headers signed: `(request-target) host date digest`
- Actor discovery via WebFinger (`/.well-known/webfinger`)
- Instance metadata via NodeInfo (`/.well-known/nodeinfo`)
- Inbox handler must validate signature before processing
- AP types: User=Person, Character=Person, Game=Collection, Report=Article, Quote=Note
- Link requests (Claim/Adopt/Fork) use AP Offer type
- No direct HTTP calls in views — use Celery tasks (or sync fallback) for federation delivery
