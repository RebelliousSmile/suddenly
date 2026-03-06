# Decision: Fediverse crypto standards alignment

| Field   | Value              |
| ------- | ------------------ |
| ID      | DEC-018            |
| Date    | 2026-03-06         |
| Feature | ActivityPub        |
| Status  | Accepted           |

## Context

US-01 requires generating RSA keys for new users. Before implementing, we validated our crypto choices against Mastodon and BookWyrm to ensure Fediverse interoperability.

## Decision

Confirm current crypto implementation as Fediverse-aligned. No LD-Signatures support.

### Validated standards

| Aspect | Standard | Source |
|--------|----------|--------|
| RSA key size | 2048-bit | Mastodon + BookWyrm |
| Algorithm | rsa-sha256 (RSASSA-PKCS1-v1_5 + SHA-256) | Mastodon + BookWyrm |
| Public key format | SPKI PEM (`BEGIN PUBLIC KEY`) | Mastodon + BookWyrm |
| Private key format | PKCS8 PEM (internal only, never transmitted) | Compatible |
| HTTP Signatures | draft-cavage-http-signatures | Mastodon + BookWyrm |
| Signed headers (GET) | `(request-target) host date` | Mastodon + BookWyrm |
| Signed headers (POST) | `(request-target) host date digest` | Mastodon + BookWyrm |
| Digest | `SHA-256={base64}` | Mastodon + BookWyrm |
| keyId | `{actor_url}#main-key` | Mastodon + BookWyrm |
| LD-Signatures | Not implemented, not planned | Mastodon discourages it |

### Actor publicKey JSON-LD structure

```json
{
  "@context": [
    "https://www.w3.org/ns/activitystreams",
    "https://w3id.org/security/v1"
  ],
  "publicKey": {
    "id": "https://domain/users/username#main-key",
    "owner": "https://domain/users/username",
    "publicKeyPem": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
  }
}
```

### Content-Type conventions

| Direction | Content-Type |
|-----------|-------------|
| Sending (POST to inbox) | `application/ld+json; profile="https://www.w3.org/ns/activitystreams"` |
| Fetching (GET actor) | `Accept: application/activity+json, application/ld+json` |
| Serving actor | Content negotiation on both above |
| WebFinger | `application/jrd+json` |
| NodeInfo | `application/json` |

## Alternatives Considered

| Alternative | Pros | Cons | Rejected because |
| ----------- | ---- | ---- | ---------------- |
| RSA 4096 | Stronger keys | Slower signing, no Fediverse precedent | No interop benefit, 2048 is universal |
| Ed25519 | Faster, modern | Not supported by Mastodon/BookWyrm yet | Would break federation |
| LD-Signatures | Relay forwarding | Mastodon discourages, outdated spec | No benefit for Suddenly use case |

## Consequences

- `generate_key_pair()` in `signatures.py` is confirmed correct — no changes needed
- Actor serializer must include `publicKey` with `#main-key` fragment and `security/v1` context
- Known robustness issues in `verify_signature` (signature age, key re-fetch, parsing) tracked separately
