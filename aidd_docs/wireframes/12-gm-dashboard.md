# 12 — Dashboard Game Master

## Vue "Mes PNJ" (`/characters/mine/`) — US-14

Page dediee au GM pour voir tous ses PNJ et les demandes en cours.

> **Legende des pastilles.** Les schemas ci-dessous nomment les pastilles par leur **role**, pas
> par leur teinte : `(pending)` = demande en attente (`color.semantic.warning`), `(claimed)` =
> Retcon accepte (`color.domain.claimed`), `(adopted)` = PNJ adopte (`color.domain.adopted`),
> `(forked)` = personnage derive (`color.domain.forked`). Une pastille ne suffit jamais seule :
> elle accompagne toujours un libelle (`usage.rules[state-colour-icon]`).

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  Mes personnages                                                 |
|                                                                  |
|  [Tous]  [PNJ disponibles]  [En attente]  [Lies]  <- onglets    |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  PNJ avec demandes en attente (2)            (pending) Priorite |
|                                                                  |
|  +------------------------------------------------------------+  |
|  | +------+  Viktor                                           |  |
|  | |avatar|  (vert) PNJ disponible  ·  City of Mist          |  |
|  | +------+  5 apparitions  ·  2 citations                    |  |
|  |                                                             |  |
|  |  (bell) 2 demandes en attente :                            |  |
|  |                                                             |  |
|  |  1. @bob veut ADOPTER          il y a 2h    [Traiter ->]  |  |
|  |  2. @charlie veut DERIVER      il y a 1j    (en file)     |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  +------------------------------------------------------------+  |
|  | +------+  Ombra                                            |  |
|  | |avatar|  (vert) PNJ disponible  ·  Blades in the Dark    |  |
|  | +------+  3 apparitions  ·  0 citation                     |  |
|  |                                                             |  |
|  |  (bell) 1 demande en attente :                             |  |
|  |                                                             |  |
|  |  1. @eve veut RECLAMER          il y a 3j   [Traiter ->]  |  |
|  +------------------------------------------------------------+  |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  PNJ disponibles sans demande (4)                                |
|                                                                  |
|  +----------+ +----------+ +----------+ +----------+            |
|  | Fenris   | | Nova     | | Thane    | | Asha     |            |
|  | Ironsworn| | BitD     | | CoM      | | CoM      |            |
|  | 8 app.   | | 1 app.   | | 2 app.   | | 3 app.   |            |
|  | Fiche -> | | Fiche -> | | Fiche -> | | Fiche -> |            |
|  +----------+ +----------+ +----------+ +----------+            |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Personnages lies (3)                                            |
|                                                                  |
|  +------------------------------------------------------------+  |
|  | Kael  (ambre) Reclame par @frank                            |  |
|  |   Lien : Retcon  ·  Sequence : "Le retour du prodigue"     |  |
|  |   Sequence publiee le 20 fev 2026                           |  |
|  +------------------------------------------------------------+  |
|  | Lyra  (adopted) Adoptee par @bob                            |  |
|  |   Lien : Adoption · Sequence : "La rencontre au carrefour" |  |
|  |   Sequence en brouillon                  [Voir sequence ->] |  |
|  +------------------------------------------------------------+  |
|  | Shadow Viktor  (violet) Derive par @dave                    |  |
|  |   Lien : Derivation · Viktor reste PNJ                      |  |
|  +------------------------------------------------------------+  |
|                                                                  |
+------------------------------------------------------------------+
```

## Dashboard GM (`/dashboard/`) — synthese

Vue optionnelle accessible depuis le profil ou le header (si le user a des parties).

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  Tableau de bord                                                 |
|                                                                  |
|  +---------------------------+  +---------------------------+    |
|  | (book-open) Mes parties   |  | (users) Mes personnages   |    |
|  |                           |  |                           |    |
|  |  3 parties actives        |  |  12 personnages           |    |
|  |  8 CRs ce mois            |  |  6 PNJ disponibles       |    |
|  |                           |  |  3 demandes en attente   |    |
|  |  [Voir mes parties ->]    |  |  [Voir mes persos ->]    |    |
|  +---------------------------+  +---------------------------+    |
|                                                                  |
|  +---------------------------+  +---------------------------+    |
|  | (bell) A traiter          |  | (edit) Sequences          |    |
|  |                           |  |                           |    |
|  |  3 demandes de lien       |  |  1 brouillon en cours    |    |
|  |  en attente de reponse    |  |  0 publication proposee  |    |
|  |                           |  |                           |    |
|  |  [Gerer les demandes ->]  |  |  [Voir les sequences ->] |    |
|  +---------------------------+  +---------------------------+    |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Activite recente sur mes PNJ                                    |
|                                                                  |
|  (pending) @bob demande l'Adoption de Viktor        il y a 2h  |
|  (claimed) @frank a accepte le Retcon de Kael        il y a 1j  |
|  (forked) @dave a derive Shadow Viktor de Viktor     il y a 3j  |
|                                                                  |
+------------------------------------------------------------------+
```

## Arbitrage en contexte (inline sur fiche personnage)

Alternative a la page dediee `09-links.md` : le GM peut aussi traiter
les demandes directement depuis la fiche du PNJ.

```
+------------------------------------------------------------------+
|  (sur la fiche de Viktor, visible uniquement pour le createur)   |
|                                                                  |
|  Demandes en attente (2)                                         |
|                                                                  |
|  +------------------------------------------------------------+  |
|  | (pending) ADOPT — @bob                         il y a 2h   |  |
|  |                                                             |  |
|  | "J'aimerais reprendre Viktor dans ma campagne              |  |
|  |  Ironsworn..."                                              |  |
|  |                                                             |  |
|  | [Accepter]  [Refuser]                                      |  |
|  +------------------------------------------------------------+  |
|  | (gray) FORK — @charlie                    (en file, 2e)    |  |
|  |                                                             |  |
|  | "Je voudrais creer Lyra, inspiree de Viktor..."            |  |
|  +------------------------------------------------------------+  |
|                                                                  |
+------------------------------------------------------------------+
```
