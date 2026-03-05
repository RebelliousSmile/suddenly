# API Documentation

## Authentication & Authorization

- **Authentication**: Session (`SessionAuthentication`)
- **Authorization**: `IsAuthenticatedOrReadOnly` — reads public, writes require login
- **ActivityPub**: HTTP Signatures for federated requests
- **Pagination**: `PageNumberPagination`, `PAGE_SIZE=20`
- **Schema**: `/api/schema/` — Swagger: `/api/docs/` — ReDoc: `/api/redoc/`

## Endpoints

### REST API (`/api/`)

- `GET/POST /api/games/` — list / create games
- `GET/PUT/PATCH/DELETE /api/games/{id}/` — game detail
- `GET /api/characters/` — list characters (filterable: `?available=true`)
- `GET /api/characters/search/?q=` — full-text search
- `GET/PUT/PATCH/DELETE /api/characters/{id}/` — character detail
- `POST /api/characters/{id}/claim/` — create claim request
- `POST /api/characters/{id}/adopt/` — create adopt request
- `POST /api/characters/{id}/fork/` — create fork request
- `POST /api/link-requests/{id}/accept/` — accept (character creator only)
- `POST /api/link-requests/{id}/reject/` — reject (character creator only)
- `GET/POST /api/reports/` — list / create reports
- `POST /api/reports/{id}/publish/` — publish draft report

### ActivityPub (`application/activity+json`)

**Acteurs** : User (Person), Character (Person), Game (Group)

| Acteur | Endpoints |
|--------|-----------|
| User | `GET /users/{username}` · `POST /users/{username}/inbox` · `GET /users/{username}/outbox` · `GET /users/{username}/followers` |
| Game | `GET /games/{id}` · `POST /games/{id}/inbox` · `GET /games/{id}/outbox` |
| Character | `GET /characters/{id}` · `POST /characters/{id}/inbox` · `GET /characters/{id}/outbox` |

**Endpoints globaux** :

| Endpoint | Usage |
|----------|-------|
| `GET /.well-known/webfinger?resource=acct:user@domain` | Découverte d'acteurs |
| `GET /.well-known/nodeinfo` | NodeInfo index |
| `GET /nodeinfo/2.0` | Détails instance |
| `POST /inbox` | Shared inbox |

### Autres

- `GET /health/` — `{"status": "ok"}`
- `/admin/` — Django admin
- `/accounts/` — django-allauth
- `GET /@{username}` — user profile page

## Request/Response Formats

- REST: `Content-Type: application/json`
- ActivityPub: `Content-Type: application/activity+json`
- Paginated: `{ count, next, previous, results[] }`
- Errors: `{ detail }` or `{ field: [errors] }`

## Activités ActivityPub supportées

| Activité | Acteur | Objet | Usage |
|----------|--------|-------|-------|
| Follow | User | User/Character/Game | Suivre |
| Accept | User | Follow/Offer | Accepter |
| Reject | User | Follow/Offer | Refuser |
| Create | User | Report/Quote/Character | Publier |
| Update | User | Report/Quote/Character | Modifier |
| Delete | User | Report/Quote | Supprimer |
| Announce | User | Report | Partager |
| Offer | User | Claim/Adopt/Fork | Proposer lien |

## Namespace Suddenly

Extensions ActivityPub spécifiques : `https://suddenly.social/ns#`

| Propriété | Description |
|-----------|-------------|
| `suddenly:status` | Statut du personnage (NPC/PC/CLAIMED/ADOPTED/FORKED) |
| `suddenly:originGame` | Partie d'origine du personnage |
| `suddenly:creator` | Créateur original |
| `suddenly:appearances` | Apparitions dans les reports |
| `suddenly:quotes` | Citations du personnage |
| `suddenly:links` | Liens Claim/Adopt/Fork |
| `suddenly:gameSystem` | Système de jeu |
| `suddenly:targetCharacter` | PNJ cible (pour Offer) |
| `suddenly:proposedCharacter` | PJ proposé (pour Claim) |
| `suddenly:relationship` | Type de relation (pour Fork) |

## HTTP Signatures

Toutes les requêtes POST vers les inboxes sont signées :

```
headers: (request-target) host date digest
algorithm: rsa-sha256
keyId: https://instance/actor#main-key
```

Vérification : récupérer `publicKey.publicKeyPem` de l'acteur, reconstruire la signature string, vérifier RSA-SHA256.

## Compatibilité Mastodon

| Type Suddenly | Affiché comme |
|---------------|---------------|
| Report (Article) | Article |
| Quote (Note) | Note |
| Character (Person) | Person |
| Offer(Claim/Adopt/Fork) | Non envoyé aux instances non-Suddenly |
