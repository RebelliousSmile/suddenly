# 07 — Personnages (Characters)

## Liste / recherche (`/characters/`) — US-07

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  Personnages                                                     |
|                                                                  |
|  +-----------------------------------------------------+        |
|  | (users) Instance | (globe) Fediverse |               |        |
|  +-----------------------------------------------------+        |
|  (alpine:tabs, par defaut "Instance")                            |
|                                                                  |
|  +-----------------------------------------------+              |
|  | (search) {Rechercher un personnage...}        |              |
|  +-----------------------------------------------+              |
|  hx-get="/htmx/characters/search/?scope={tab}"                   |
|  hx-trigger="keyup changed delay:300ms"                          |
|  hx-target="#character-results"                                  |
|                                                                  |
|  Statut: [Tous v]  Tags: [Tous             v]                   |
|                                                                  |
+------------------------------------------------------------------+
|  id="character-results"                                          |
|                                                                  |
|  +------------+ +------------+ +------------+ +------------+    |
|  |            | |            | |            | |            |    |
|  | (avatar)   | | (avatar)   | | (avatar)   | | (avatar)   |    |
|  | Viktor     | | Ombra      | | Kael       | | Fenris     |    |
|  | (o) Dispo  | | (o) Dispo  | | (*) Retcon | | (o) Dispo  |    |
|  |            | |            | |            | |            |    |
|  | City of    | | Blades in  | | City of    | | Ironsworn  |    |
|  | Mist       | | the Dark   | | Mist       | |            |    |
|  |            | |            | |            | |            |    |
|  | 5 appar.   | | 3 appar.   | | 1 appar.   | | 8 appar.   |    |
|  | 2 citations| | 0 citation | | 0 citation | | 4 citations|    |
|  |            | |            | |            | |            |    |
|  | [Lier a    | | [Lier a    | |            | | [Lier a    |    |
|  |  mon       | |  mon       | |            | |  mon       |    |
|  |  histoire] | |  histoire] | |            | |  histoire] |    |
|  +------------+ +------------+ +------------+ +------------+    |
|                                                                  |
|                    [Charger plus...]                              |
|                    (hx-trigger="revealed")                        |
|                                                                  |
+------------------------------------------------------------------+
```

Un seul bouton [Lier a mon histoire] par PNJ disponible, visible au hover.
Ouvre le flow guide (voir `09-links.md`).

En onglet **Fediverse**, les cards affichent le badge instance :
`(globe) suddenly.games` sous le nom de la partie d'origine.
La recherche FTS interroge les instances connues (plus lent, spinner).

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
|  Lier ce personnage a votre histoire              US-10          |
|  (visible uniquement si PNJ disponible + user authentifie)       |
|                                                                  |
|  +------------------------------------------------------------+  |
|  |                                                            |  |
|  |  Ce PNJ vous inspire ? Integrez-le dans votre             |  |
|  |  histoire en un clic.                                      |  |
|  |                                                            |  |
|  |        [Lier a mon histoire ->]  btn-primary               |  |
|  |                                                            |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  --- clic ---> flow guide (voir 09-links.md)                     |
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
|  (visible uniquement si le personnage a un parent ou des derives)|
|                                                                  |
|  Viktor (PNJ, origin)                                            |
|    +-- Lyra (PJ, derive par @bob)                               |
|    |     +-- Kira (PJ, derive par @charlie)                     |
|    +-- Shadow Viktor (PJ, derive par @dave)                      |
|                                                                  |
+------------------------------------------------------------------+
```

### Fiche personnage — bandeau si demande en cours

```
+------------------------------------------------------------------+
|  @status_banner(type="info", icon="clock")                       |
|  Vous avez une demande d'Adoption en attente sur ce PNJ.        |
|  Envoyee il y a 2h.   [Voir ma demande]   [Annuler]             |
+------------------------------------------------------------------+
```

Ou si en file d'attente :

```
+------------------------------------------------------------------+
|  @status_banner(type="warning", icon="clock")                    |
|  Votre demande de Derivation est en file d'attente (#2).        |
|  [Voir ma demande]   [Annuler]                                   |
+------------------------------------------------------------------+
```

Le bouton [Lier a mon histoire] est masque quand une demande est active.

### Fiche personnage — variante PJ (status != NPC)

```
|  Statut : (bleu) PJ actif                                       |
|  Proprietaire : @bob                                             |
|  Lien : Adopte depuis le 10 fev 2026                            |
|  Sequence partagee : "La rencontre au carrefour"                 |
|                                                                  |
|  [Deriver ce personnage ->]  <- ouvre le flow guide en mode      |
|                                  derivation uniquement (US-17)   |
|  [Renoncer a ce personnage]* <- visible si proprietaire (US-16)  |
```

*Renonciation : voir modal dans `09-links.md`.

### Fiche personnage — variante PJ issu d'une Derivation (US-17)

La derivation en chaine est possible. La demande est envoyee au
**proprietaire actuel** (pas au createur original).

```
|  Statut : (violet) Derive                                        |
|  Proprietaire : @bob                                             |
|  Parent : Viktor (PNJ de @alice)                                 |
|  Lien : Derivation depuis le 5 mars 2026                        |
|                                                                  |
|  [Deriver ce personnage ->]  -> demande envoyee a @bob           |
```

### Fiche personnage — variante lien revoque (US-16)

```
|  Statut : (vert) PNJ disponible                                  |
|  Ancien lien : (red barre) Adopte par @bob (revoque 10 mars)    |
|  Sequence : "La rencontre au carrefour" (lien revoque)           |
|                                                                  |
|  [Lier a mon histoire ->]                                        |
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
|  @status_banner(type="info", icon="globe")                       |
|  Ce personnage est heberge sur une instance distante.            |
|  Les interactions passent par ActivityPub.                        |
|                                                                  |
|  [Suivre]   [Lier a mon histoire ->]                             |
```
