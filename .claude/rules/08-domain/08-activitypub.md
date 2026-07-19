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

## Signature verification (DEC-020)

- Public keys cached in `PublicKeyCache` DB table — not Redis (compatible mode minimal)
- On verification failure with cached key: re-fetch once, then reject
- `URLField` for AP actor URLs must use `max_length=500` (default 200 is too short)

## Inbox rate limiting (DEC-021)

- Per-instance domain rate limiting via `django-ratelimit`
- Known instances (`FederatedServer`): 100 req/min
- Unknown instances: 10 req/min
- Rate limit check runs before `verify_signature()` to save resources

## Federation

- Actor discovery via WebFinger (`/.well-known/webfinger`)
- Instance metadata via NodeInfo 2.0 (`/.well-known/nodeinfo`)
- Inbox handler must validate signature before processing
- AP types: User=Person, Character=Person, Game=Collection, Report=Article, Quote=Note
- Link requests (Claim/Adopt/Fork) use AP Offer type
- No direct HTTP calls in views — use Celery tasks (or sync fallback) for federation delivery
- Exception: `verify_signature()` does synchronous HTTP fetch (required before processing)

## Suddenly instance detection

- Identify Suddenly instances via NodeInfo `software.name == "suddenly"`
- Store detected instance type on `FederatedServer` row
- Filter Suddenly-only activities (Offer for links) at the outbox before sending
- Never send Suddenly-only activities to non-Suddenly instances
  **Why:** non-Suddenly software cannot interpret Claim/Adopt/Fork semantics; sending wastes delivery and pollutes remote inboxes.

## Custom JSON-LD namespace

- Always include `{"suddenly": "https://suddenly.social/ns#"}` in `@context` of Suddenly-specific activities
- Namespace URL must remain stable — moving it is a breaking federation change
- Custom properties used: `suddenly:status`, `suddenly:originGame`, `suddenly:creator`, `suddenly:gameSystem`, `suddenly:sheetUrl`, `suddenly:relationship`, `suddenly:targetCharacter`, `suddenly:proposedCharacter`, `suddenly:previousReport`, `suddenly:temporalKind`, `suddenly:temporalAnchor`, `suddenly:temporalLabel`
- Fiction order (Report `Article`) federates as **soft IRIs**: `suddenly:previousReport` / `suddenly:temporalAnchor` carry the linked report's `ap_id`/local URL — never a hard FK. On receipt, resolving the IRI to a known `ap_id` sets the FK **and clears the IRI** (XOR CheckConstraint `report_previous_local_xor_remote`).
- Mastodon ignores unknown properties — non-Suddenly instances still receive valid AS2 types

## Remote fetch — SSRF hardening

- One entry point for every remote AP/WebFinger GET: `fetch_ap_json(url, *, accept, timeout)` in `_http.py` — never raw `httpx`/`requests` in views or resolvers
- `fetch_ap_json` resolves DNS once, rejects private/loopback/link-local IPs, then pins the connection to that IP (`_validate_and_pin`) — closes the DNS-rebind window
- WebFinger and actor resolution both route through it — no bypass
- On `Update(Person)` with a rotated key, invalidate the cached actor key (`_invalidate_actor_key`) before trusting the next signature

## Outbox collection

- `totalItems` counts the full collection, never the sliced page — count on the base queryset before pagination
  **Why:** a page-length `totalItems` misreports the collection size to remote crawlers and breaks paging.

## Offer federation — canonical format (DEC-038)

- Canonical Offer = `serializers.serialize_link_request` — the single wire format
- `object.type` = `suddenly:Claim` / `suddenly:Adopt` / `suddenly:Fork`; target NPC in top-level `target`; message in `object.content`; proposed PC in `object.proposedCharacter`
- Receive only via `inbox.py::handle_offer` — never reintroduce the `Relationship` form
- Resolve a target/proposed character with `_resolve_character_by_actor_url` (remote `ap_id`, else parse the local URL); unknown remote proposed PC → `get_or_create_remote_character` (fetch via `fetch_ap_json`, SSRF-safe)
- Correlate a federated Accept/Reject by `LinkRequest.origin_offer_id` (the requester's Offer `id`), never by the local PK — set at receipt in `handle_offer`, read in `send_accept_activity`/`send_reject_activity`
- Requester-side state after Accept is rebuilt by `LinkService.reconstruct_remote_accept` (CharacterLink + SharedSequence + notification), idempotent on replay — never call `accept_request` on the requester side
- Accepting a CLAIM with an unresolved `proposed_character` raises `ValidationError` (never let `CharacterLink.source` IntegrityError surface); `reconstruct_remote_accept` mirrors the same null guard
- Inbox dispatch lives in `inbox.py` only — `tasks.py` has no incoming-activity handlers
- Authorize an inbound Accept/Reject with `_remote_response_authorized` — signature auth proves the *sender*, not entitlement
- Sender domain must match a target-controller domain: `target_character.ap_id` **or** its `owner`/`creator` `ap_id` (the Offer was delivered there) — else a peer that learned the Offer id could forge acceptance (fabricated `CharacterLink`, new FORK PC)
- Lock the `LinkRequest` row (`select_for_update`, DEC-035) in `reconstruct_remote_accept` and `handle_reject` — federation retries redeliver; without the lock the loser hits the `OneToOne` `IntegrityError`
- Store `origin_offer_id` only when it fits `URLField(max_length=500)` — untrusted remote input, `.create()` skips `full_clean`

## Cross-instance request timeouts

- Cross-instance link requests expire after 30 days (fixed at MVP)
- Status `EXPIRED` set by daily Celery cleanup task
- Notify the requester when their request expires
  **Why:** prevents ghost requests piling up in the queue; 30 days fits async TTRPG play cadence.
