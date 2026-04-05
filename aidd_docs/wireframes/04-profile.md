# 04 — Profil utilisateur

## Profil public (`/users/{username}/`) — US-01

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  +--------+  Alice Dupont                                        |
|  | avatar |  @alice@suddenly.social                              |
|  |  (lg)  |                                                      |
|  +--------+  Joueuse de City of Mist et Blades in the Dark.     |
|              Mes PNJ cherchent des histoires.                    |
|                                                                  |
|              (link) ActivityPub: @alice@suddenly.social           |
|                                                                  |
|              [Suivre]           [Modifier le profil]*            |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Parties recentes                                      [Voir +] |
|                                                                  |
|  +------------------+ +------------------+ +------------------+  |
|  | @game_card       | | @game_card       | | @game_card       |  |
|  |                  | |                  | |                  |  |
|  | City of Mist     | | Blades in the    | | Ironsworn        |  |
|  | 12 CRs           | | Dark - 8 CRs    | | Solo - 3 CRs     |  |
|  +------------------+ +------------------+ +------------------+  |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Personnages                                           [Voir +] |
|                                                                  |
|  +------------------+ +------------------+ +------------------+  |
|  | @character_card  | | @character_card  | | @character_card  |  |
|  |                  | |                  | |                  |  |
|  | Viktor (PNJ)    | | Lyra (PJ)       | | Ombra (PNJ)      |  |
|  | (vert) Dispo     | | (bleu) Actif    | | (vert) Dispo     |  |
|  +------------------+ +------------------+ +------------------+  |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Derniers comptes-rendus                               [Voir +] |
|                                                                  |
|  @report_card                                                    |
|  @report_card                                                    |
|  @report_card                                                    |
|                                                                  |
+------------------------------------------------------------------+
```

*`[Modifier le profil]` visible uniquement si `user == profile_user`.

## Edition profil (`/users/{username}/edit/`)

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|                  +----------------------------+                  |
|                  |                            |                  |
|                  |   Modifier mon profil      |                  |
|                  |                            |                  |
|                  |  Nom d'affichage           |                  |
|                  |  {_Alice Dupont____________}|                 |
|                  |                            |                  |
|                  |  Biographie                |                  |
|                  |  {________________________}|                  |
|                  |  {  Joueuse de City of    }|                  |
|                  |  {  Mist et Blades...     }|                  |
|                  |  {________________________}|                  |
|                  |                            |                  |
|                  |  Avatar                    |                  |
|                  |  +----------------------+  |                  |
|                  |  | (upload) Glisser     |  |                  |
|                  |  | une image ici ou     |  |                  |
|                  |  | cliquer pour choisir |  |                  |
|                  |  +----------------------+  |                  |
|                  |  [x] Supprimer l'avatar    |                  |
|                  |                            |                  |
|                  |  Langue du contenu         |                  |
|                  |  {_fr______________________}|                 |
|                  |                            |                  |
|                  |  Langues preferees         |                  |
|                  |  {_fr, en_________________}|                  |
|                  |                            |                  |
|                  |  [ ] Afficher le contenu   |                  |
|                  |      sans langue definie   |                  |
|                  |                            |                  |
|                  |  [Enregistrer]  Annuler    |                  |
|                  |                            |                  |
|                  +----------------------------+                  |
|                                                                  |
+------------------------------------------------------------------+
```
