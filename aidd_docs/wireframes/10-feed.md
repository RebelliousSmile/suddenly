# 10 — Fil d'actualite, portee et Follow

## Concept de portee (scope)

Comme sur Mastodon, le contenu est organise en 3 portees :

| Portee | Icone | Contenu | Equivalent Mastodon |
|--------|-------|---------|-------------------|
| **Abonnements** | `i-lucide-home` | CRs des joueurs/parties que je suis | Home |
| **Instance** | `i-lucide-users` | Tout le contenu public de mon instance | Local |
| **Fediverse** | `i-lucide-globe` | Contenu federe des instances connectees | Federated |

Cette portee est visible comme onglets sur le feed, et comme filtre
sur les pages de liste (personnages, parties).

---

## Fil d'actualite (`/feed/`) — US-12

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  Fil d'actualite                                                 |
|                                                                  |
|  +-----------------------------------------------------+        |
|  | (home) Abonnements | (users) Instance | (globe) Fediverse |  |
|  +-----------------------------------------------------+        |
|  (alpine:tabs, par defaut "Abonnements")                         |
|                                                                  |
+------------------------------------------------------------------+
```

### Onglet Abonnements (defaut)

```
+------------------------------------------------------------------+
|                                                                  |
|  PNJ disponibles dans vos parties suivies                        |
|  (section ambre, visible si des PNJ existent)                    |
|                                                                  |
|  +----------+ +----------+ +----------+                          |
|  | @npc_highlight                                                |
|  | Viktor   | | Fenris   | | Nova     |                          |
|  | City of  | | Ironsworn| | BitD     |                          |
|  | Mist     | |          | |          |                          |
|  +----------+ +----------+ +----------+                          |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Sequences Partagees recentes                                    |
|  (section violette, visible si pertinent)                        |
|                                                                  |
|  +------------------------------------------------------------+  |
|  | "La rencontre au carrefour"                                 |  |
|  | Entre @alice et @bob · Viktor <-> Shadow Viktor             |  |
|  +------------------------------------------------------------+  |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Filtres : [Tout] [CRs] [Sequences] [PNJ]                       |
|  id="feed-list"                                                  |
|                                                                  |
|  @feed_item(report=...) — @alice dans City of Mist               |
|  @feed_item(report=...) — @dave dans Ironsworn                   |
|  ...                                                             |
|                                                                  |
|  (hx-trigger="revealed" -> page suivante)                        |
|                                                                  |
+------------------------------------------------------------------+
```

### Etat vide — Abonnements

```
+------------------------------------------------------------------+
|  @empty_state(icon="home")                                       |
|                                                                  |
|  Votre fil est vide pour l'instant.                              |
|                                                                  |
|  Suivez des joueurs ou des parties pour voir leurs               |
|  publications ici.                                               |
|                                                                  |
|  [Explorer mon instance]   [Rechercher sur le Fediverse]         |
+------------------------------------------------------------------+
```

### Onglet Instance

Tout le contenu public de mon instance, sans filtre d'abonnement.
Ideal pour decouvrir les joueurs locaux.

```
+------------------------------------------------------------------+
|                                                                  |
|  (users) Contenu de {{ SITE_NAME }}                              |
|                                                                  |
|  Filtres : [Tout] [CRs] [Sequences] [PNJ]                       |
|  id="instance-feed"                                              |
|  hx-get="/feed/instance/"                                        |
|                                                                  |
|  @feed_item — @alice dans City of Mist                           |
|  @feed_item — @charlie dans Vampire                              |
|  @feed_item — @eve dans Ironsworn                                |
|  ...                                                             |
|                                                                  |
|  (hx-trigger="revealed")                                         |
|                                                                  |
+------------------------------------------------------------------+
```

Les items du fil Instance n'affichent pas le badge (globe) — tout est local.

### Onglet Fediverse

Contenu provenant des instances federees. Plus lent a charger
(aggrege le contenu recu via ActivityPub).

```
+------------------------------------------------------------------+
|                                                                  |
|  (globe) Fediverse                                               |
|                                                                  |
|  Filtres : [Tout] [CRs] [Sequences] [PNJ]                       |
|  id="fediverse-feed"                                             |
|  hx-get="/feed/federated/"                                       |
|                                                                  |
|  +------------------------------------------------------------+  |
|  | +------+  @alice@suddenly.games dans City of Mist           |  |
|  | |avatar|  (globe) suddenly.games             il y a 4h      |  |
|  | +------+  Session 8 : Le marche des ombres                  |  |
|  |                                                             |  |
|  |  [Viktor] [Nyx]                                             |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  +------------------------------------------------------------+  |
|  | +------+  @frank@jdr.social dans Cyberpunk RED              |  |
|  | |avatar|  (globe) jdr.social                 il y a 1j      |  |
|  | +------+  Run 12 : Interference                             |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  (hx-trigger="revealed")                                         |
|                                                                  |
+------------------------------------------------------------------+
```

Chaque item du fil Fediverse affiche le **badge instance** :
`(globe) nom.instance` en gris a cote du timestamp.

### Etat vide — Fediverse

```
+------------------------------------------------------------------+
|  @empty_state(icon="globe")                                      |
|                                                                  |
|  Aucun contenu federe pour l'instant.                            |
|                                                                  |
|  Le contenu apparaitra quand des joueurs d'autres instances      |
|  publieront des CRs ou que vous suivrez des acteurs distants.    |
|                                                                  |
|  [Rechercher sur le Fediverse]                                   |
+------------------------------------------------------------------+
```

---

## Badge d'origine instance

Un badge discret indiquant l'instance d'origine. Visible sur :
- Feed Fediverse (toujours)
- Feed Abonnements (si contenu distant)
- Fiches personnage/partie distantes
- Profils distants

```
Format inline :    (globe) suddenly.games
Format card :      texte gris sous le nom d'auteur
Classe :           text-xs text-gray-500 flex items-center gap-1
                   + i-lucide-globe
```

Pas de badge si le contenu est local (implicite = local).

---

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

---

## Page Explorer (`/explore/`) — US-22

La page Explorer est la porte d'entree pour decouvrir du contenu.
Elle distingue explicitement le contenu local et federe.

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
|  Tapez @user@instance pour une recherche federee                 |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  (users) Sur {{ SITE_NAME }}                                     |
|                                                                  |
|  Parties actives                                                 |
|  @game_card  @game_card  @game_card                              |
|                                                                  |
|  Joueurs actifs                                                  |
|  +------+ @alice  ·  12 parties  ·  [Suivre]                    |
|  +------+ @bob    ·   8 parties  ·  [Suivre]                    |
|  +------+ @charlie · 5 parties   ·  [Suivre]                    |
|                                                                  |
|  PNJ disponibles                                                 |
|  @character_card  @character_card  @character_card               |
|                                                                  |
|  [Voir tout le contenu local ->]                                 |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  (globe) Sur le Fediverse                                        |
|                                                                  |
|  Instances Suddenly connues                                      |
|                                                                  |
|  +------------------------------------------------------------+  |
|  | suddenly.games — Suddenly 0.1.0 — 84 joueurs               |  |
|  | "Instance francophone de JDR narratif"                      |  |
|  | [Explorer cette instance ->]                                |  |
|  +------------------------------------------------------------+  |
|  +------------------------------------------------------------+  |
|  | jdr.social — Suddenly 0.1.0 — 42 joueurs                   |  |
|  | "JDR et fiction collaborative"                              |  |
|  | [Explorer cette instance ->]                                |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  Joueurs federes populaires                                      |
|  +------+ @alice@suddenly.games · (globe) · [Suivre]            |
|  +------+ @frank@jdr.social · (globe) · [Suivre]                |
|                                                                  |
|  [Rechercher sur le Fediverse ->]                                |
|                                                                  |
+------------------------------------------------------------------+
```

### Explorer une instance distante (`/explore/suddenly.games/`)

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  (globe) suddenly.games                                          |
|  Suddenly 0.1.0 — 84 joueurs — Federee depuis jan. 2026        |
|                                                                  |
|  "Instance francophone de JDR narratif"                          |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Parties publiques                                               |
|  @game_card (avec badge globe)  @game_card  @game_card           |
|                                                                  |
|  Joueurs                                                         |
|  +------+ @alice@suddenly.games · 12 parties · [Suivre]         |
|  +------+ @bob@suddenly.games · 8 parties · [Suivre]            |
|                                                                  |
|  PNJ disponibles                                                 |
|  @character_card (avec badge globe)  @character_card             |
|                                                                  |
+------------------------------------------------------------------+
```
