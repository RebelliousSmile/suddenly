# 07 — Personnages (Characters)

## Liste / recherche (`/characters/`) — US-07

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  Personnages                                                     |
|                                                                  |
|  +-----------------------------------------------+              |
|  | (search) {Rechercher un personnage...}        |              |
|  +-----------------------------------------------+              |
|  hx-get="/htmx/characters/search/"                               |
|  hx-trigger="keyup changed delay:300ms"                          |
|  hx-target="#character-results"                                  |
|                                                                  |
|  Statut: [Tous v]  Systeme: [Tous          v]                   |
|                                                                  |
+------------------------------------------------------------------+
|  id="character-results"                                          |
|                                                                  |
|  +------------+ +------------+ +------------+ +------------+    |
|  |            | |            | |            | |            |    |
|  | (avatar)   | | (avatar)   | | (avatar)   | | (avatar)   |    |
|  | Viktor     | | Ombra      | | Kael       | | Fenris     |    |
|  | (o) Dispo  | | (o) Dispo  | | (*) Reclame| | (o) Dispo  |    |
|  |            | |            | |            | |            |    |
|  | City of    | | Blades in  | | City of    | | Ironsworn  |    |
|  | Mist       | | the Dark   | | Mist       | |            |    |
|  |            | |            | |            | |            |    |
|  | 5 appar.   | | 3 appar.   | | 1 appar.   | | 8 appar.   |    |
|  | 2 citations| | 0 citation | | 0 citation | | 4 citations|    |
|  |            | |            | |            | |            |    |
|  |  [Adopter] | |  [Adopter] | |            | |  [Adopter] |    |
|  |  [Reclamer]| |  [Reclamer]| |            | |  [Reclamer]|    |
|  |  [Deriver] | |  [Deriver] | |            | |  [Deriver] |    |
|  +------------+ +------------+ +------------+ +------------+    |
|  +------------+ +------------+ +------------+ +------------+    |
|  | ...        | | ...        | | ...        | | ...        |    |
|  +------------+ +------------+ +------------+ +------------+    |
|                                                                  |
|                    [Charger plus...]                              |
|                    (hx-trigger="revealed")                        |
|                                                                  |
+------------------------------------------------------------------+
```

Les boutons [Adopter]/[Reclamer]/[Deriver] apparaissent au hover.
Seuls les PNJ disponibles (status=NPC) montrent les boutons d'action.

## Fiche personnage (`/characters/{slug}/`) — US-06

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  +----------+                                                    |
|  |          |  Viktor                                            |
|  | (avatar) |  (o) PNJ disponible         [Suivre]              |
|  |  (xl)    |                                                    |
|  |          |  Origine : City of Mist — Saison 2                |
|  +----------+  Cree par : @alice                                |
|                Proprietaire : —                                  |
|                                                                  |
|  (external-link) Fiche technique : lien_externe                  |
|  (activity) AP : @viktor@suddenly.social                         |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Description                                                     |
|                                                                  |
|  Ancien detective prive reconverti en consultant pour            |
|  le Quartier des Reflets. Viktor ne croit pas aux mythes         |
|  — ou du moins, il essaie de ne pas y croire.                   |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Actions                                              US-10      |
|                                                                  |
|  +------------------+ +------------------+ +------------------+  |
|  | (merge) Reclamer | | (heart) Adopter  | | (git-fork) Fork  |  |
|  |                  | |                  | |                  |  |
|  | "C'etait mon PJ  | | "Je reprends ce  | | "Je cree un PJ   |  |
|  |  depuis le debut" | |  PNJ comme PJ"   | |  inspire de lui" |  |
|  +------------------+ +------------------+ +------------------+  |
|                                                                  |
|  --- clic ---> modal (voir 09-links.md)                          |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Apparitions (5)                                      US-06      |
|                                                                  |
|  +------+------+------+------+                                   |
|  | Date | CR   | Partie| Role |                                  |
|  +------+------+------+------+                                   |
|  | mars | L'Oracle    | CoM  | Principal  |                      |
|  | fev  | Le pont     | CoM  | Secondaire |                      |
|  | fev  | Rencontre   | CoM  | Mentionne  |                      |
|  | jan  | Le rituel   | CoM  | Principal  |                      |
|  | jan  | Premiere    | CoM  | Principal  |                      |
|  +------+------+------+------+                                   |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Citations (2)                                        US-08      |
|  id="quotes-section"                                             |
|                                                                  |
|  (voir wireframe 08-quotes.md)                                   |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Lignee                                               US-17      |
|  (visible uniquement si le personnage a un parent ou des forks) |
|                                                                  |
|  Viktor (PNJ, origin)                                            |
|    +-- Lyra (PJ, fork par @bob)                                 |
|    |     +-- Kira (PJ, fork par @charlie)                       |
|    +-- Shadow Viktor (PJ, fork par @dave)                        |
|                                                                  |
+------------------------------------------------------------------+
```

### Fiche personnage — variante PJ (status != NPC)

Les boutons Adopter/Reclamer disparaissent. A la place :

```
|  Statut : (bleu) PJ actif                                       |
|  Proprietaire : @bob                                             |
|  Lien : Adopte depuis le 10 fev 2026                            |
|  Sequence partagee : "La rencontre au carrefour"                 |
|                                                                  |
|  [Deriver ce personnage]     <- Fork toujours disponible (US-17) |
|  [Renoncer a ce personnage]* <- visible si proprietaire (US-16)  |
```

*Renonciation : voir modal dans `09-links.md`.

### Fiche personnage — variante PJ issu d'un Fork (US-17)

Le bouton [Deriver] est visible car un PJ forke peut etre re-forke.
La demande est envoyee au **proprietaire** (pas au createur original).

```
|  Statut : (violet) Derive                                        |
|  Proprietaire : @bob                                             |
|  Parent : Viktor (PNJ de @alice)                                 |
|  Lien : Fork depuis le 5 mars 2026                              |
|                                                                  |
|  [Deriver ce personnage]  -> demande envoyee a @bob              |
```

### Fiche personnage — variante lien revoque (US-16)

```
|  Statut : (vert) PNJ disponible                                  |
|  Ancien lien : (red barré) Adopte par @bob (revoque 10 mars)    |
|  Sequence : "La rencontre au carrefour" (lien revoque)           |
|                                                                  |
|  [Adopter]  [Reclamer]  [Deriver]                                |
```

### Fiche personnage — variante acteur distant (US-22)

```
|  +----------+                                                    |
|  |          |  Viktor                                            |
|  | (avatar) |  (vert) PNJ disponible                             |
|  |  (xl)    |  (globe) suddenly.games                            |
|  |          |                                                    |
|  +----------+  Origine : City of Mist                            |
|                Cree par : @alice@suddenly.games                   |
|                                                                  |
|  (info) Ce personnage est heberge sur une instance distante.     |
|  Les interactions passent par ActivityPub.                        |
|                                                                  |
|  [Suivre]  [Adopter]  [Reclamer]  [Deriver]                     |
```
