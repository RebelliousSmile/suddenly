---
paths:
  - "suddenly/activitypub/**"
---

# ActivityPub domain rules

## Crypto standards (DEC-018)

- RSA 2048-bit keys, algorithm `rsa-sha256` (RSASSA-PKCS1-v1_5 + SHA-256)
- Public key: SPKI PEM (`BEGIN PUBLIC KEY`), private key: PKCS8 PEM (internal only)
- No LD-Signatures — Mastodon discourages it, not needed for Suddenly

## HTTP Signatures

- All outgoing requests signed with HTTP Signatures (draft-cavage-http-signatures)
- Headers signed (GET): `(request-target) host date`
- Headers signed (POST): `(request-target) host date digest`
- Digest: `SHA-256={base64}`
- keyId format: `{actor_url}#main-key`

## Content-Type

- Sending (POST to inbox): `application/ld+json; profile="https://www.w3.org/ns/activitystreams"`
- Fetching (GET actor): `Accept: application/activity+json, application/ld+json`
- WebFinger responses: `application/jrd+json`
- NodeInfo responses: `application/json`

## Actor publicKey

- Actor JSON-LD must include `https://w3id.org/security/v1` in `@context`
- `publicKey` object: `id` (actor#main-key), `owner` (actor url), `publicKeyPem`

## Federation

- Actor discovery via WebFinger (`/.well-known/webfinger`)
- Instance metadata via NodeInfo 2.0 (`/.well-known/nodeinfo`)
- Inbox handler must validate signature before processing
- AP types: User=Person, Character=Person, Game=Collection, Report=Article, Quote=Note
- Link requests (Claim/Adopt/Fork) use AP Offer type
- No direct HTTP calls in views — use Celery tasks (or sync fallback) for federation delivery
