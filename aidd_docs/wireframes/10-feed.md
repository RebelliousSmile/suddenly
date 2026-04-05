# 10 — Fil d'actualite et Follow

## Fil d'actualite (`/feed/`) — US-12

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  Mon fil d'actualite                                             |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  PNJ disponibles dans vos parties suivies                        |
|  (section ambre, visible si des PNJ existent)                    |
|                                                                  |
|  +----------+ +----------+ +----------+                          |
|  | Viktor   | | Fenris   | | Nova     |                          |
|  | City of  | | Ironsworn| | BitD     |                          |
|  | Mist     | |          | |          |                          |
|  | Fiche -> | | Fiche -> | | Fiche -> |                          |
|  +----------+ +----------+ +----------+                          |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Sequences Partagees recentes                                    |
|  (section violette, visible si pertinent)                        |
|                                                                  |
|  +------------------------------------------------------------+  |
|  | "La rencontre au carrefour"                                 |  |
|  | Entre @alice et @bob                                        |  |
|  | Viktor <-> Shadow Viktor                                    |  |
|  +------------------------------------------------------------+  |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Comptes-rendus recents                                          |
|  id="feed-list"                                                  |
|                                                                  |
|  +------------------------------------------------------------+  |
|  | +------+  @alice dans City of Mist          il y a 2h      |  |
|  | |avatar|                                                    |  |
|  | +------+  Session 12 : L'Oracle brise                      |  |
|  |                                                             |  |
|  |  La nuit tombait sur le Quartier des Reflets...             |  |
|  |                                                             |  |
|  |  [Viktor] [Lyra] [Ombra]                                   |  |
|  |                                                             |  |
|  |  (heart) 4  (message) 2  (share)                           |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  +------------------------------------------------------------+  |
|  | +------+  @dave dans Ironsworn               il y a 1j     |  |
|  | |avatar|                                                    |  |
|  | +------+  Jour 47 : La forge silencieuse                   |  |
|  |                                                             |  |
|  |  Le marteau retomba une derniere fois...                    |  |
|  |                                                             |  |
|  |  [Fenris] [Thane]                                           |  |
|  |                   [Fenris(o)] PNJ disponible !              |  |
|  |                                                             |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  (hx-trigger="revealed" -> page suivante)                        |
|  Chargement...                                                   |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Votre fil est vide.                                             |
|  Suivez des joueurs ou des parties pour voir                     |
|  leurs publications ici.                                         |
|  [Explorer les parties]                                          |
|                                                                  |
+------------------------------------------------------------------+
```

Le dernier bloc (fil vide) est affiche uniquement si aucun abonnement.

## Bouton Follow (partial HTMX reutilisable)

Inclus sur : profil joueur, page partie, fiche personnage.

### Etat "pas abonne"

```
+----------------------------+
| hx-post="/follow/{type}/{id}/"
| hx-target="this"
| hx-swap="outerHTML"
|
| [Suivre]  (btn-primary)    |
+----------------------------+
```

### Etat "abonne"

```
+----------------------------+
| hx-post="/unfollow/{type}/{id}/"
| hx-target="this"
| hx-swap="outerHTML"
|
| [Abonne (check)]  (btn-secondary, hover: "Ne plus suivre")
+----------------------------+
```

### Comportement

- Clic [Suivre] -> `hx-post` -> retourne le partial "abonne"
- Clic [Abonne] -> `hx-post` -> retourne le partial "pas abonne"
- Si cible distante : Follow(status=PENDING) cote local, envoi AP Follow
- Si cible locale : Follow(status=ACCEPTED) immediat

## Page Explorer (`/explore/`)

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  Explorer                                                        |
|                                                                  |
|  +-----------------------------------------------+              |
|  | (search) {Rechercher joueurs, parties, persos} |              |
|  +-----------------------------------------------+              |
|                                                                  |
|  [Joueurs]  [Parties]  [Personnages]   <- onglets               |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Parties populaires                                              |
|                                                                  |
|  @game_card  @game_card  @game_card                              |
|                                                                  |
|  Joueurs actifs                                                  |
|                                                                  |
|  +------+ @alice  ·  12 parties  ·  [Suivre]                    |
|  +------+ @bob    ·   8 parties  ·  [Suivre]                    |
|  +------+ @charlie · 5 parties  ·  [Suivre]                    |
|                                                                  |
|  PNJ recemment crees                                             |
|                                                                  |
|  @character_card  @character_card  @character_card               |
|                                                                  |
+------------------------------------------------------------------+
```
