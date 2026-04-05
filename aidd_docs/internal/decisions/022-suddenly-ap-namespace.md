# ADR-022: Suddenly ActivityPub Namespace

## Status
Accepted — 2026-04-05

## Context
Suddenly uses custom ActivityPub properties not defined in the AS2 vocabulary.
Remote Suddenly instances need to understand these properties to interoperate
on Suddenly-specific features (character status, game system, link requests).

## Decision

Suddenly defines a custom JSON-LD namespace:

```json
{
  "@context": [
    "https://www.w3.org/ns/activitystreams",
    "https://w3id.org/security/v1",
    {"suddenly": "https://suddenly.social/ns#"}
  ]
}
```

### Custom properties

| Property | Type | Used on | Description |
|----------|------|---------|-------------|
| `suddenly:status` | string | Character | Character status (npc, pc, claimed, adopted, forked) |
| `suddenly:originGame` | URL | Character | Game where character first appeared |
| `suddenly:creator` | URL | Character | User who created the character |
| `suddenly:gameSystem` | string | Game | TTRPG system name |
| `suddenly:sheetUrl` | URL | Character | External character sheet link |
| `suddenly:relationship` | string | Offer | Link type (claim, adopt, fork) |
| `suddenly:targetCharacter` | URL | Offer | NPC being claimed/adopted/forked |
| `suddenly:proposedCharacter` | URL | Offer | Existing PC proposed for Claim |

### Compatibility

- Mastodon ignores unknown properties (safe)
- Non-Suddenly instances receive standard AP types only (Article, Note, Person)
- Suddenly-only activities (Offer for links) are NOT sent to non-Suddenly instances
  (checked via `FederatedServer.is_suddenly_instance()`)

## Consequences

- Other Suddenly instances can parse character metadata
- Mastodon compatibility preserved (unknown props ignored)
- Namespace URL must be stable (breaking change if moved)
