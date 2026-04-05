# 11 — Notifications

## Centre de notifications (`/notifications/`) — US-20

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  Notifications                          [Tout marquer comme lu]  |
|                                                                  |
|  Filtre: [Toutes v]                                              |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  +------------------------------------------------------------+  |
|  | (*) (merge) Demande de lien                     il y a 2h  |  |
|  |                                                  (non lu)   |  |
|  |  @bob veut adopter votre PNJ Viktor                        |  |
|  |  [Voir la demande ->]                                      |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  +------------------------------------------------------------+  |
|  | (*) (check) Demande acceptee                    il y a 1j  |  |
|  |                                                  (non lu)   |  |
|  |  @dave a accepte votre demande d'Adoption sur Fenris       |  |
|  |  [Voir la Sequence Partagee ->]                            |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  +------------------------------------------------------------+  |
|  |     (book-open) Nouveau CR                      il y a 2j  |  |
|  |                                                    (lu)     |  |
|  |  @alice a publie "L'Oracle brise" dans City of Mist        |  |
|  |  [Lire le CR ->]                                           |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  +------------------------------------------------------------+  |
|  |     (user-plus) Nouveau follower                il y a 3j  |  |
|  |                                                    (lu)     |  |
|  |  @charlie vous suit                                        |  |
|  |  [Voir le profil ->]                                       |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  +------------------------------------------------------------+  |
|  |     (edit) Sequence Partagee                    il y a 4j  |  |
|  |                                                    (lu)     |  |
|  |  @alice propose de publier "La rencontre au carrefour"     |  |
|  |  [Voir la sequence ->]                                     |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|                    [Charger plus...]                              |
|                                                                  |
+------------------------------------------------------------------+
```

### Badge dans le header

```
+------------------------------------------------------------------+
|  ...    (cloche)[3]   [avatar v]                                 |
+------------------------------------------------------------------+
           ^
           | nombre de notifications non lues
           | HTMX polling toutes les 30s ou SSE
```

### Types de notifications

| Type | Icone | Couleur | Declencheur |
|------|-------|---------|-------------|
| Demande de lien | (merge) | amber | LinkRequest creee sur mon PNJ |
| Reponse demande | (check)/(x) | emerald/red | Ma demande acceptee/refusee |
| Nouveau CR | (book-open) | indigo | Joueur/partie suivi publie |
| **Recommandation** | **(sparkles)** | **accent** | **Quelqu'un a recommande votre CR** |
| **Mention** | **(at-sign)** | **blue** | **Quelqu'un vous a mentionne dans un CR** |
| **Invitation** | **(send)** | **primary** | **Quelqu'un vous invite a decouvrir un CR/PNJ** |
| Nouveau follower | (user-plus) | blue | Quelqu'un me suit |
| SharedSequence | (edit) | violet | Invitation, proposition publication |
| Revocation | (alert-triangle) | red | Lien revoque |

## Parametres notifications (`/settings/notifications/`) — US-21

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  Preferences de notification                                     |
|                                                                  |
|  +------------------------------------------------------------+  |
|  |                     | In-app | Email  |                     |  |
|  +---------------------+--------+--------+                     |  |
|  | Demandes de lien    | [x]    | [x]    |                     |  |
|  | Reponses            | [x]    | [x]    |                     |  |
|  | SharedSequence      | [x]    | [x]    |                     |  |
|  | Nouveaux CRs        | [x]    | [ ]    |                     |  |
|  | Recommandations     | [x]    | [ ]    |                     |  |
|  | Mentions            | [x]    | [x]    |                     |  |
|  | Invitations         | [x]    | [x]    |                     |  |
|  | Nouveaux followers  | [x]    | [ ]    |                     |  |
|  +---------------------+--------+--------+                     |  |
|  |                                                             |  |
|  |  (info) Les notifications in-app sont toujours actives.     |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  [Enregistrer]                                                   |
|                                                                  |
+------------------------------------------------------------------+
```

Les `[x]` in-app sont desactives (toujours coches, non modifiables).
