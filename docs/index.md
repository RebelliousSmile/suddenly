# Suddenly

**Federated shared fiction network** — where NPCs from one game can become player characters in another.

Players publish session reports, and mentioned characters can be claimed, adopted, or forked by other players across instances via ActivityPub.

## What is Suddenly?

Suddenly is a self-hostable federated platform for tabletop RPG players. It connects instances together so characters and stories can travel across communities.

Key concepts:

- **Reports** — session write-ups published by players
- **Characters** — PCs and NPCs that appear in reports
- **Games** — campaigns and one-shots grouping reports
- **Federation** — instances communicate via ActivityPub

## Character links

When a character from one game appears in another group's story, three relationship types are possible:

| Type | Description | Result |
|------|-------------|--------|
| **Claim** | "Your NPC was my PC all along" | Retcon, NPC replaced |
| **Adopt** | "I'm taking over your NPC" | NPC becomes a PC |
| **Fork** | "My PC is inspired by your NPC" | New linked PC |

## Self-hosting

Suddenly runs on any server with Python and PostgreSQL — no Docker required.

- [Deployment on a VPS](deployment/vps.md) *(coming soon)*
- [Deployment on Alwaysdata](deployment/alwaysdata.md) *(coming soon)*
- [Deployment with Docker](deployment/docker.md) *(coming soon)*

## Contributing

- [Adding a translation](translations.md)
- [GitHub repository](https://github.com/RebelliousSmile/suddenly)
