# 14 — Federation cross-instance

## Recherche federee (`/search/`) — US-22

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  Recherche                                                       |
|                                                                  |
|  +-----------------------------------------------+              |
|  | (search) {Rechercher sur le Fediverse...}     |  [Chercher]  |
|  +-----------------------------------------------+              |
|                                                                  |
|  Exemples : "Viktor", "@alice", "@alice@suddenly.games",         |
|             "City of Mist"                                       |
|                                                                  |
|  [Local]  [Federe]  [Tout]     <- onglets de portee             |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Resultats locaux (3)                                            |
|                                                                  |
|  Joueurs                                                         |
|  +------+ @alice  ·  12 parties  ·  [Suivre]                    |
|  |avatar|                                                        |
|  +------+                                                        |
|                                                                  |
|  Parties                                                         |
|  @game_card (compact) — City of Mist                             |
|                                                                  |
|  Personnages                                                     |
|  @character_card (mini) — Viktor (PNJ)                           |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Resultats federes (chargement...)                               |
|  hx-get="/search/federated/?q=..."                               |
|  hx-trigger="load"                                               |
|                                                                  |
|  (spinner) Interrogation des instances connues...                |
|                                                                  |
|  --- apres chargement --->                                       |
|                                                                  |
|  Resultats federes (2)                                           |
|                                                                  |
|  +------+ @alice@suddenly.games                                  |
|  |avatar|  (globe) suddenly.games                                |
|  +------+  3 parties publiques  ·  [Suivre]                     |
|                                                                  |
|  +------+ Viktor (PNJ)                                           |
|  |avatar|  (globe) suddenly.games                                |
|  +------+  City of Mist  ·  [Voir la fiche ->]                  |
|                                                                  |
+------------------------------------------------------------------+
```

### Recherche par identifiant federe

Saisir `@alice@suddenly.games` declenche un WebFinger lookup :

```
+------------------------------------------------------------------+
|  +-----------------------------------------------+              |
|  | @alice@suddenly.games                         |  [Chercher]  |
|  +-----------------------------------------------+              |
|                                                                  |
|  (spinner) Resolution WebFinger...                               |
|                                                                  |
|  --- apres resolution --->                                       |
|                                                                  |
|  -> Redirection vers le profil distant de @alice@suddenly.games  |
+------------------------------------------------------------------+
```

## Profil distant (`/remote/@alice@suddenly.games/`) — US-22

Variante de `04-profile.md` pour un acteur federe.

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  (globe) Profil distant — suddenly.games                         |
|                                                                  |
|  +--------+  Alice Dupont                                        |
|  | avatar |  @alice@suddenly.games                               |
|  |  (lg)  |                                                      |
|  +--------+  Joueuse de City of Mist et Blades in the Dark.     |
|                                                                  |
|              [Suivre]                                             |
|                                                                  |
|  (info) Ce profil est heberge sur suddenly.games.                |
|  Les donnees affichees sont celles partagees via ActivityPub.    |
|  Voir le profil complet sur suddenly.games ->                    |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Parties publiques (3)                                           |
|                                                                  |
|  @game_card — City of Mist (suddenly.games)                      |
|  @game_card — Blades in the Dark (suddenly.games)                |
|  @game_card — Ironsworn (suddenly.games)                         |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Personnages publics (5)                                         |
|                                                                  |
|  @character_card — Viktor (PNJ)                                  |
|  @character_card — Ombra (PNJ)                                   |
|  @character_card — Kael (Reclame)                                |
|  ...                                                             |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Derniers comptes-rendus                                         |
|                                                                  |
|  @report_card — Session 12 : L'Oracle brise                     |
|  @report_card — Session 11 : Le pont des ombres                 |
|                                                                  |
+------------------------------------------------------------------+
```

## Rendu Mastodon / ActivityPub — US-24

Ces wireframes representent ce que voit un utilisateur Mastodon dans
son fil quand il suit un acteur Suddenly.

### CR vu comme Article depuis Mastodon

```
+------------------------------------------------------------+
|  (mastodon UI)                                              |
|                                                             |
|  Alice (@alice@suddenly.social)                  il y a 2h |
|                                                             |
|  [Article] Session 12 : L'Oracle brise                     |
|                                                             |
|  La nuit tombait sur le Quartier des Reflets quand          |
|  Viktor poussa la porte du bar...                           |
|                                                             |
|  Personnages : Viktor, Lyra, Ombra                          |
|  Partie : City of Mist — Saison 2                           |
|                                                             |
|  Lire la suite sur suddenly.social ->                       |
|                                                             |
|  (star) (boost) (reply) (bookmark)                          |
+------------------------------------------------------------+
```

### Citation vue comme Note depuis Mastodon

```
+------------------------------------------------------------+
|  (mastodon UI)                                              |
|                                                             |
|  Viktor (@viktor@suddenly.social)                il y a 1j |
|                                                             |
|  "Les mythes ne meurent pas, ils changent                   |
|   simplement de visage."                                    |
|                                                             |
|  — Viktor, dans "L'Oracle brise"                            |
|  suddenly.social/characters/viktor                          |
|                                                             |
|  (star) (boost) (reply) (bookmark)                          |
+------------------------------------------------------------+
```

### Activites Suddenly-only (non envoyees a Mastodon)

Les activites suivantes sont reservees aux instances Suddenly :

| Activite | Type AP | Mastodon recoit ? |
|----------|---------|-------------------|
| Publication CR | Create(Article) | Oui |
| Citation publique | Create(Note) | Oui |
| Demande Claim/Adopt/Fork | Offer | **Non** |
| Acceptation/Refus | Accept/Reject | **Non** |
| SharedSequence publiee | Create(Article) | Oui |

L'instance verifie `FederatedServer.application_type == "suddenly"`
avant d'envoyer les activites Suddenly-only.

## NodeInfo / WebFinger (endpoints techniques)

Pas de wireframe UI — ces endpoints retournent du JSON.

```
GET /.well-known/nodeinfo
-> { "links": [{ "href": "/nodeinfo/2.1", "rel": "..." }] }

GET /nodeinfo/2.1
-> { "software": { "name": "suddenly", "version": "0.1.0" },
     "protocols": ["activitypub"],
     "usage": { "users": { "total": 142 } } }

GET /.well-known/webfinger?resource=acct:alice@suddenly.social
-> { "subject": "acct:alice@suddenly.social",
     "links": [{ "rel": "self", "type": "application/activity+json",
                 "href": "https://suddenly.social/users/alice" }] }
```
