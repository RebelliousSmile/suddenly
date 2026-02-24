# Suddenly — Spécification ActivityPub

**Version** : 1.0.0
**Basé sur** : ActivityPub W3C, ActivityStreams 2.0
**Inspiré de** : BookWyrm

---

## TL;DR

```
Acteurs     : User (Person), Character (Person), Game (Group)
Objets      : Report (Article), Quote (Note)
Activités   : Follow, Create, Update, Delete, Offer, Accept, Reject
Spécifique  : Offer(Claim), Offer(Adopt), Offer(Fork)
```

---

## Table des Matières

1. [Acteurs](#acteurs)
2. [Objets](#objets)
3. [Activités](#activités)
4. [Endpoints](#endpoints)
5. [Signatures HTTP](#signatures-http)
6. [Compatibilité Mastodon](#compatibilité-mastodon)
7. [Exemples Complets](#exemples-complets)

---

## Acteurs

Suddenly définit **3 types d'acteurs** ActivityPub :

### User (Person)

Le joueur, propriétaire de parties et personnages.

```json
{
  "@context": [
    "https://www.w3.org/ns/activitystreams",
    "https://w3id.org/security/v1",
    {
      "suddenly": "https://suddenly.social/ns#",
      "PropertyValue": "schema:PropertyValue",
      "value": "schema:value"
    }
  ],
  "id": "https://instance.example/users/alice",
  "type": "Person",
  "preferredUsername": "alice",
  "name": "Alice Dupont",
  "summary": "<p>Joueuse solo, fan de City of Mist</p>",
  "inbox": "https://instance.example/users/alice/inbox",
  "outbox": "https://instance.example/users/alice/outbox",
  "followers": "https://instance.example/users/alice/followers",
  "following": "https://instance.example/users/alice/following",
  "publicKey": {
    "id": "https://instance.example/users/alice#main-key",
    "owner": "https://instance.example/users/alice",
    "publicKeyPem": "-----BEGIN PUBLIC KEY-----\n..."
  },
  "icon": {
    "type": "Image",
    "mediaType": "image/png",
    "url": "https://instance.example/media/avatars/alice.png"
  },
  "endpoints": {
    "sharedInbox": "https://instance.example/inbox"
  },
  "suddenly:games": "https://instance.example/users/alice/games",
  "suddenly:characters": "https://instance.example/users/alice/characters"
}
```

**Champs spécifiques Suddenly** :
- `suddenly:games` : Collection des parties du joueur
- `suddenly:characters` : Collection des PJ du joueur

### Character (Person)

Un personnage joueur (PJ) ou non-joueur (PNJ). Les personnages sont des acteurs à part entière, suivables.

```json
{
  "@context": [
    "https://www.w3.org/ns/activitystreams",
    "https://w3id.org/security/v1",
    {
      "suddenly": "https://suddenly.social/ns#"
    }
  ],
  "id": "https://instance.example/characters/detective-marlowe",
  "type": "Person",
  "preferredUsername": "detective-marlowe",
  "name": "Détective Marlowe",
  "summary": "<p>Un détective privé hanté par son passé. Mythos: L'Ombre du Doute.</p>",
  "inbox": "https://instance.example/characters/detective-marlowe/inbox",
  "outbox": "https://instance.example/characters/detective-marlowe/outbox",
  "followers": "https://instance.example/characters/detective-marlowe/followers",
  "publicKey": {
    "id": "https://instance.example/characters/detective-marlowe#main-key",
    "owner": "https://instance.example/characters/detective-marlowe",
    "publicKeyPem": "-----BEGIN PUBLIC KEY-----\n..."
  },
  "icon": {
    "type": "Image",
    "mediaType": "image/png",
    "url": "https://instance.example/media/characters/marlowe.png"
  },
  "attributedTo": "https://instance.example/users/alice",
  "suddenly:status": "PC",
  "suddenly:originGame": "https://instance.example/games/city-of-mist-campaign",
  "suddenly:creator": "https://instance.example/users/alice",
  "suddenly:appearances": "https://instance.example/characters/detective-marlowe/appearances",
  "suddenly:quotes": "https://instance.example/characters/detective-marlowe/quotes",
  "suddenly:links": "https://instance.example/characters/detective-marlowe/links"
}
```

**Champs spécifiques Suddenly** :

| Champ | Type | Description |
|-------|------|-------------|
| `attributedTo` | User | Propriétaire actuel (owner) |
| `suddenly:status` | Enum | `NPC`, `PC`, `CLAIMED`, `ADOPTED`, `FORKED` |
| `suddenly:originGame` | Game | Partie d'origine |
| `suddenly:creator` | User | Créateur original |
| `suddenly:appearances` | Collection | Comptes-rendus où il apparaît |
| `suddenly:quotes` | Collection | Citations du personnage |
| `suddenly:links` | Collection | Liens (Claim/Adopt/Fork) |

### Game (Group)

Une partie/campagne. **Acteur suivable** qui publie les comptes-rendus.

```json
{
  "@context": [
    "https://www.w3.org/ns/activitystreams",
    "https://w3id.org/security/v1",
    {
      "suddenly": "https://suddenly.social/ns#"
    }
  ],
  "id": "https://instance.example/games/city-of-mist-campaign",
  "type": "Group",
  "preferredUsername": "city-of-mist-campaign",
  "name": "Ombres sur la Cité",
  "summary": "<p>Une campagne City of Mist en solo.</p>",
  "inbox": "https://instance.example/games/city-of-mist-campaign/inbox",
  "outbox": "https://instance.example/games/city-of-mist-campaign/outbox",
  "followers": "https://instance.example/games/city-of-mist-campaign/followers",
  "publicKey": {
    "id": "https://instance.example/games/city-of-mist-campaign#main-key",
    "owner": "https://instance.example/games/city-of-mist-campaign",
    "publicKeyPem": "-----BEGIN PUBLIC KEY-----\n..."
  },
  "attributedTo": "https://instance.example/users/alice",
  "published": "2024-01-15T10:00:00Z",
  "updated": "2024-03-20T15:30:00Z",
  "endpoints": {
    "sharedInbox": "https://instance.example/inbox"
  },
  "suddenly:gameSystem": "City of Mist",
  "suddenly:reports": "https://instance.example/games/city-of-mist-campaign/reports",
  "suddenly:characters": "https://instance.example/games/city-of-mist-campaign/characters"
}
```

**Champs spécifiques Suddenly** :
- `suddenly:gameSystem` : Système de jeu (City of Mist, D&D, etc.)
- `suddenly:reports` : Collection des comptes-rendus
- `suddenly:characters` : Collection des personnages originaires

**Avantages de Game comme acteur** :
- Les utilisateurs peuvent suivre une partie directement
- Les nouveaux Reports sont publiés via l'outbox de la partie
- Séparation claire des flux : suivre Alice ≠ suivre sa campagne

---

## Objets

### Report (Article)

Un compte-rendu de partie. Type `Article` pour compatibilité Mastodon.

```json
{
  "@context": [
    "https://www.w3.org/ns/activitystreams",
    {
      "suddenly": "https://suddenly.social/ns#"
    }
  ],
  "id": "https://instance.example/reports/session-5-the-reveal",
  "type": "Article",
  "name": "Session 5 : La Révélation",
  "content": "<p>Marlowe a enfin découvert la vérité sur @detective-marlowe...</p>",
  "contentMap": {
    "fr": "<p>Marlowe a enfin découvert la vérité sur @detective-marlowe...</p>"
  },
  "language": "fr",
  "attributedTo": "https://instance.example/users/alice",
  "published": "2024-03-20T15:30:00Z",
  "to": ["https://www.w3.org/ns/activitystreams#Public"],
  "cc": [
    "https://instance.example/users/alice/followers",
    "https://instance.example/characters/detective-marlowe/followers"
  ],
  "tag": [
    {
      "type": "Mention",
      "href": "https://instance.example/characters/detective-marlowe",
      "name": "@detective-marlowe@instance.example"
    },
    {
      "type": "Mention",
      "href": "https://other.example/characters/mysterious-stranger",
      "name": "@mysterious-stranger@other.example"
    }
  ],
  "suddenly:game": "https://instance.example/games/city-of-mist-campaign",
  "suddenly:appearances": [
    {
      "character": "https://instance.example/characters/detective-marlowe",
      "role": "MAIN"
    },
    {
      "character": "https://other.example/characters/mysterious-stranger",
      "role": "SUPPORTING"
    }
  ]
}
```

**Gestion des langues** :
- `language` : Code ISO 639-1 de la langue principale
- `contentMap` : Versions multilingues du contenu (optionnel)
- Mastodon utilise ces champs pour le filtrage par langue

**Rôles d'apparition** :
- `MAIN` : Personnage principal de la scène
- `SUPPORTING` : Personnage secondaire
- `MENTIONED` : Simplement mentionné

### Quote (Note)

Une citation mémorable. Type `Note` pour compatibilité Mastodon.

```json
{
  "@context": [
    "https://www.w3.org/ns/activitystreams",
    {
      "suddenly": "https://suddenly.social/ns#"
    }
  ],
  "id": "https://instance.example/quotes/marlowe-truth",
  "type": "Note",
  "content": "<p>« La vérité, c'est comme la pluie sur cette ville. Elle finit toujours par tomber. »</p>",
  "attributedTo": "https://instance.example/users/alice",
  "published": "2024-03-20T16:00:00Z",
  "to": ["https://www.w3.org/ns/activitystreams#Public"],
  "cc": ["https://instance.example/characters/detective-marlowe/followers"],
  "tag": [
    {
      "type": "Mention",
      "href": "https://instance.example/characters/detective-marlowe",
      "name": "@detective-marlowe@instance.example"
    }
  ],
  "suddenly:character": "https://instance.example/characters/detective-marlowe",
  "suddenly:context": "Face au miroir, après avoir découvert son passé.",
  "suddenly:report": "https://instance.example/reports/session-5-the-reveal"
}
```

---

## Activités

### Activités Standard

#### Follow

Suivre un utilisateur ou un personnage.

```json
{
  "@context": "https://www.w3.org/ns/activitystreams",
  "id": "https://other.example/activities/follow-123",
  "type": "Follow",
  "actor": "https://other.example/users/bob",
  "object": "https://instance.example/characters/detective-marlowe"
}
```

#### Accept / Reject

Réponse à un Follow ou une Offer.

```json
{
  "@context": "https://www.w3.org/ns/activitystreams",
  "id": "https://instance.example/activities/accept-456",
  "type": "Accept",
  "actor": "https://instance.example/users/alice",
  "object": {
    "id": "https://other.example/activities/follow-123",
    "type": "Follow",
    "actor": "https://other.example/users/bob",
    "object": "https://instance.example/characters/detective-marlowe"
  }
}
```

#### Create

Créer un nouveau contenu (Report, Quote, Character).

```json
{
  "@context": "https://www.w3.org/ns/activitystreams",
  "id": "https://instance.example/activities/create-789",
  "type": "Create",
  "actor": "https://instance.example/users/alice",
  "object": {
    "id": "https://instance.example/reports/session-5-the-reveal",
    "type": "Article",
    "name": "Session 5 : La Révélation",
    "content": "..."
  },
  "to": ["https://www.w3.org/ns/activitystreams#Public"],
  "cc": ["https://instance.example/users/alice/followers"]
}
```

#### Update

Mettre à jour un contenu existant.

```json
{
  "@context": "https://www.w3.org/ns/activitystreams",
  "id": "https://instance.example/activities/update-101",
  "type": "Update",
  "actor": "https://instance.example/users/alice",
  "object": {
    "id": "https://instance.example/reports/session-5-the-reveal",
    "type": "Article",
    "name": "Session 5 : La Révélation (mise à jour)",
    "content": "..."
  }
}
```

#### Delete

Supprimer un contenu.

```json
{
  "@context": "https://www.w3.org/ns/activitystreams",
  "id": "https://instance.example/activities/delete-102",
  "type": "Delete",
  "actor": "https://instance.example/users/alice",
  "object": "https://instance.example/quotes/old-quote"
}
```

#### Announce

Partager/booster un contenu (Report d'une autre instance).

```json
{
  "@context": "https://www.w3.org/ns/activitystreams",
  "id": "https://instance.example/activities/announce-103",
  "type": "Announce",
  "actor": "https://instance.example/users/alice",
  "object": "https://other.example/reports/amazing-session",
  "to": ["https://www.w3.org/ns/activitystreams#Public"],
  "cc": ["https://instance.example/users/alice/followers"]
}
```

### Activités Spécifiques Suddenly

#### Offer (Claim)

Proposer un Claim : "Ton PNJ c'était mon PJ depuis le début."

```json
{
  "@context": [
    "https://www.w3.org/ns/activitystreams",
    {
      "suddenly": "https://suddenly.social/ns#"
    }
  ],
  "id": "https://other.example/activities/offer-claim-200",
  "type": "Offer",
  "actor": "https://other.example/users/bob",
  "object": {
    "type": "suddenly:Claim",
    "suddenly:targetCharacter": "https://instance.example/characters/mysterious-stranger",
    "suddenly:proposedCharacter": "https://other.example/characters/jack-shadow",
    "suddenly:message": "Jack Shadow était présent à la Cité depuis le début. Il observait Marlowe dans l'ombre, attendant le bon moment pour se révéler."
  },
  "target": "https://instance.example/users/alice",
  "to": ["https://instance.example/users/alice"]
}
```

**Champs Claim** :
- `suddenly:targetCharacter` : Le PNJ visé (sur l'instance cible)
- `suddenly:proposedCharacter` : Le PJ qui "était" ce PNJ (sur l'instance source)
- `suddenly:message` : Justification narrative

#### Offer (Adopt)

Proposer une Adoption : "Je reprends ton PNJ comme mon PJ."

```json
{
  "@context": [
    "https://www.w3.org/ns/activitystreams",
    {
      "suddenly": "https://suddenly.social/ns#"
    }
  ],
  "id": "https://other.example/activities/offer-adopt-201",
  "type": "Offer",
  "actor": "https://other.example/users/bob",
  "object": {
    "type": "suddenly:Adopt",
    "suddenly:targetCharacter": "https://instance.example/characters/mysterious-stranger",
    "suddenly:message": "Je voudrais reprendre l'Étranger Mystérieux comme PJ dans ma propre campagne. Son histoire m'inspire !"
  },
  "target": "https://instance.example/users/alice",
  "to": ["https://instance.example/users/alice"]
}
```

#### Offer (Fork)

Proposer un Fork : "Je crée un PJ inspiré de ton PNJ."

```json
{
  "@context": [
    "https://www.w3.org/ns/activitystreams",
    {
      "suddenly": "https://suddenly.social/ns#"
    }
  ],
  "id": "https://other.example/activities/offer-fork-202",
  "type": "Offer",
  "actor": "https://other.example/users/bob",
  "object": {
    "type": "suddenly:Fork",
    "suddenly:targetCharacter": "https://instance.example/characters/mysterious-stranger",
    "suddenly:relationship": "nephew",
    "suddenly:message": "Je crée le neveu de l'Étranger Mystérieux, qui a hérité de ses pouvoirs mais pas de ses secrets."
  },
  "target": "https://instance.example/users/alice",
  "to": ["https://instance.example/users/alice"]
}
```

**Champs Fork** :
- `suddenly:relationship` : Type de lien (nephew, former_partner, clone, etc.)

#### Accept (Link)

Accepter un Claim/Adopt/Fork.

```json
{
  "@context": [
    "https://www.w3.org/ns/activitystreams",
    {
      "suddenly": "https://suddenly.social/ns#"
    }
  ],
  "id": "https://instance.example/activities/accept-link-300",
  "type": "Accept",
  "actor": "https://instance.example/users/alice",
  "object": {
    "id": "https://other.example/activities/offer-claim-200",
    "type": "Offer"
  },
  "result": {
    "type": "suddenly:CharacterLink",
    "id": "https://instance.example/links/claim-marlowe-shadow",
    "suddenly:linkType": "CLAIM",
    "suddenly:source": "https://other.example/characters/jack-shadow",
    "suddenly:target": "https://instance.example/characters/mysterious-stranger"
  },
  "to": ["https://other.example/users/bob"]
}
```

---

## Endpoints

### Endpoints par Acteur

| Acteur | Endpoint | Description |
|--------|----------|-------------|
| User | `/@{username}` | Profil (Accept: application/activity+json) |
| User | `/@{username}/inbox` | Inbox (POST) |
| User | `/@{username}/outbox` | Outbox (GET) |
| User | `/@{username}/followers` | Collection followers |
| User | `/@{username}/following` | Collection following |
| Game | `/games/{slug}` | Profil partie (Accept: application/activity+json) |
| Game | `/games/{slug}/inbox` | Inbox partie (POST) |
| Game | `/games/{slug}/outbox` | Outbox partie (GET) - contient les Reports |
| Game | `/games/{slug}/followers` | Collection followers |
| Character | `/characters/{slug}` | Profil personnage |
| Character | `/characters/{slug}/inbox` | Inbox personnage |
| Character | `/characters/{slug}/outbox` | Outbox personnage |

### Endpoints Globaux

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/.well-known/webfinger` | GET | Découverte d'acteurs |
| `/.well-known/nodeinfo` | GET | Infos instance |
| `/nodeinfo/2.0` | GET | Détails NodeInfo |
| `/inbox` | POST | Shared inbox |

### Webfinger

```
GET /.well-known/webfinger?resource=acct:alice@instance.example
```

```json
{
  "subject": "acct:alice@instance.example",
  "aliases": [
    "https://instance.example/@alice",
    "https://instance.example/users/alice"
  ],
  "links": [
    {
      "rel": "self",
      "type": "application/activity+json",
      "href": "https://instance.example/users/alice"
    },
    {
      "rel": "http://webfinger.net/rel/profile-page",
      "type": "text/html",
      "href": "https://instance.example/@alice"
    }
  ]
}
```

**Pour les personnages** :

```
GET /.well-known/webfinger?resource=acct:detective-marlowe@instance.example
```

### NodeInfo

```
GET /.well-known/nodeinfo
```

```json
{
  "links": [
    {
      "rel": "http://nodeinfo.diaspora.software/ns/schema/2.0",
      "href": "https://instance.example/nodeinfo/2.0"
    }
  ]
}
```

```
GET /nodeinfo/2.0
```

```json
{
  "version": "2.0",
  "software": {
    "name": "suddenly",
    "version": "0.1.0"
  },
  "protocols": ["activitypub"],
  "usage": {
    "users": {
      "total": 150,
      "activeMonth": 45,
      "activeHalfyear": 100
    },
    "localPosts": 500
  },
  "openRegistrations": true,
  "metadata": {
    "nodeName": "Mon Instance Suddenly",
    "nodeDescription": "Une instance pour les rôlistes",
    "characters": 320,
    "games": 75,
    "reports": 500
  }
}
```

---

## Signatures HTTP

Toutes les requêtes POST vers les inbox doivent être signées.

### Format de Signature

```http
POST /users/alice/inbox HTTP/1.1
Host: instance.example
Date: Sun, 20 Mar 2024 15:30:00 GMT
Digest: SHA-256=X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=
Signature: keyId="https://other.example/users/bob#main-key",
           algorithm="rsa-sha256",
           headers="(request-target) host date digest",
           signature="base64signature..."
Content-Type: application/activity+json

{...activity JSON...}
```

### Algorithme de Signature

```python
# Pseudocode
headers_to_sign = ["(request-target)", "host", "date", "digest"]

signature_string = """(request-target): post /users/alice/inbox
host: instance.example
date: Sun, 20 Mar 2024 15:30:00 GMT
digest: SHA-256=X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE="""

signature = rsa_sign(signature_string, private_key)
```

### Vérification

1. Récupérer la clé publique de l'acteur (`publicKey.publicKeyPem`)
2. Reconstruire la chaîne de signature
3. Vérifier avec RSA-SHA256

---

## Compatibilité Mastodon

### Transformation des Types

| Type Suddenly | Type Mastodon | Transformation |
|---------------|---------------|----------------|
| Report (Article) | Article | Aucune |
| Quote (Note) | Note | Aucune |
| Character (Person) | Person | Compatible |
| Offer(Claim/Adopt/Fork) | — | Non fédéré vers Mastodon |

### Affichage sur Mastodon

Un **Report** apparaît comme un article avec :
- Titre du compte-rendu
- Contenu (Markdown → HTML)
- Mentions des personnages (liens)

Une **Quote** apparaît comme une note standard.

Les **Offer** (Claim/Adopt/Fork) ne sont pas envoyées aux instances non-Suddenly.

### Détection du Type d'Instance

```python
def is_suddenly_instance(actor_id: str) -> bool:
    """Vérifie si l'acteur est sur une instance Suddenly."""
    nodeinfo = fetch_nodeinfo(get_domain(actor_id))
    return nodeinfo.get("software", {}).get("name") == "suddenly"
```

---

## Exemples Complets

### Flux : Publication d'un Report

```
1. Alice écrit un compte-rendu mentionnant @mysterious-stranger@other.example

2. Suddenly crée l'activité Create(Article)

3. Envoi aux followers d'Alice (inbox de chaque follower)

4. Envoi aux followers du personnage mentionné

5. Si other.example est Suddenly : envoi complet avec suddenly:appearances
   Si other.example est Mastodon : envoi Article standard avec mentions
```

### Flux : Claim Cross-Instance

```
1. Bob (other.example) propose un Claim sur mysterious-stranger (instance.example)

2. Bob envoie Offer(Claim) à l'inbox d'Alice

3. Alice reçoit la notification

4. Alice accepte → envoie Accept à l'inbox de Bob

5. Le CharacterLink est créé sur les deux instances

6. mysterious-stranger.status devient CLAIMED

7. Les followers des deux personnages sont notifiés
```

### Flux : Follow d'un Personnage

```
1. Bob veut suivre detective-marlowe@instance.example

2. Bob envoie Follow à l'inbox du personnage

3. Suddenly vérifie les permissions (personnage public ?)

4. Si OK : Accept automatique
   Si approbation requise : notification à Alice (owner)

5. Bob est ajouté aux followers du personnage

6. Bob recevra les futures Quote et apparitions
```

---

## Namespace Suddenly

```json
{
  "suddenly": "https://suddenly.social/ns#",
  "suddenly:status": {
    "@id": "suddenly:status",
    "@type": "@vocab"
  },
  "suddenly:CharacterStatus": {
    "@id": "suddenly:CharacterStatus"
  },
  "NPC": "suddenly:NPC",
  "PC": "suddenly:PC",
  "CLAIMED": "suddenly:CLAIMED",
  "ADOPTED": "suddenly:ADOPTED",
  "FORKED": "suddenly:FORKED"
}
```

### Propriétés Suddenly

| Propriété | Type | Description |
|-----------|------|-------------|
| `suddenly:status` | CharacterStatus | Statut du personnage |
| `suddenly:originGame` | Game | Partie d'origine |
| `suddenly:creator` | User | Créateur original |
| `suddenly:appearances` | Collection | Apparitions dans les reports |
| `suddenly:quotes` | Collection | Citations |
| `suddenly:links` | Collection | Liens Claim/Adopt/Fork |
| `suddenly:game` | Game | Partie associée (pour Report) |
| `suddenly:character` | Character | Personnage associé (pour Quote) |
| `suddenly:gameSystem` | String | Système de jeu |
| `suddenly:targetCharacter` | Character | PNJ cible (pour Offer) |
| `suddenly:proposedCharacter` | Character | PJ proposé (pour Claim) |
| `suddenly:relationship` | String | Type de relation (pour Fork) |
| `suddenly:linkType` | LinkType | Type de lien (CLAIM/ADOPT/FORK) |

---

## Résumé des Activités

| Activité | Acteur | Objet | Cible | Usage |
|----------|--------|-------|-------|-------|
| Follow | User | User/Character | — | Suivre |
| Accept | User | Follow/Offer | — | Accepter |
| Reject | User | Follow/Offer | — | Refuser |
| Create | User | Report/Quote/Character | — | Publier |
| Update | User | Report/Quote/Character | — | Modifier |
| Delete | User | Report/Quote | — | Supprimer |
| Announce | User | Report | — | Partager |
| Offer | User | Claim/Adopt/Fork | User | Proposer lien |
