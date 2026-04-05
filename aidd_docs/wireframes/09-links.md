# 09 — Liens (Claim / Adopt / Fork)

## Modal de demande — US-10

Declenchee depuis la fiche personnage (`07-characters.md`).
Utilise `@modal` existant (Alpine.js, teleporte dans body).

### Adopt

```
+----------------------------------------------------------+
|                                                    [x]   |
|  Adopter Viktor                                          |
|                                                          |
|  Vous souhaitez reprendre Viktor comme votre PJ.         |
|  Le createur (@alice) devra accepter votre demande.      |
|                                                          |
|  Votre proposition narrative                              |
|  {______________________________________________________}|
|  {  Expliquez pourquoi vous voulez adopter ce            }|
|  {  personnage et comment il s'integre dans              }|
|  {  votre histoire...                                    }|
|  {______________________________________________________}|
|                                                          |
|  (info-circle) Une fois acceptee, vous co-ecrirez       |
|  une Sequence Partagee avec @alice pour sceller          |
|  la transition narrative.                                |
|                                                          |
|               [Envoyer la demande]   Annuler             |
|                                                          |
+----------------------------------------------------------+
```

### Claim (retcon)

```
+----------------------------------------------------------+
|                                                    [x]   |
|  Reclamer Viktor                                         |
|                                                          |
|  Vous affirmez que Viktor etait votre PJ depuis le       |
|  debut (retcon narratif).                                |
|                                                          |
|  Votre personnage existant (optionnel)                   |
|  {Rechercher un de vos PJ...______________________}      |
|  hx-get="/htmx/characters/suggest/?owner=me"             |
|                                                          |
|  Votre explication                                       |
|  {______________________________________________________}|
|  {______________________________________________________}|
|                                                          |
|               [Envoyer la demande]   Annuler             |
|                                                          |
+----------------------------------------------------------+
```

### Fork (derivation)

```
+----------------------------------------------------------+
|                                                    [x]   |
|  Deriver Viktor                                          |
|                                                          |
|  Vous creez un nouveau PJ inspire de Viktor.             |
|  Viktor reste PNJ — votre PJ sera un personnage          |
|  distinct lie par une lignee narrative.                   |
|                                                          |
|  Nom de votre nouveau PJ                                 |
|  {_Shadow Viktor_____________________________________}   |
|                                                          |
|  Votre proposition narrative                              |
|  {______________________________________________________}|
|  {______________________________________________________}|
|                                                          |
|               [Envoyer la demande]   Annuler             |
|                                                          |
+----------------------------------------------------------+
```

## Page de gestion des demandes (`/characters/requests/`) — US-09, US-11, US-14

Accessible depuis le header (notification badge) ou le profil.

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  Demandes de lien                                                |
|                                                                  |
|  Filtre: [Toutes v]  [Recues | Envoyees]                        |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Recues (3)                                                      |
|                                                                  |
|  +------------------------------------------------------------+  |
|  | (amber) EN ATTENTE                             il y a 2h   |  |
|  |                                                             |  |
|  | @bob veut ADOPTER votre PNJ Viktor                         |  |
|  |                                                             |  |
|  | "J'aimerais reprendre Viktor dans ma campagne             |  |
|  |  Ironsworn. Il deviendrait un ancien detective             |  |
|  |  reconverti en voyageur solitaire..."                      |  |
|  |                                                             |  |
|  | [Accepter]  [Refuser]  [Voir la fiche de Viktor]           |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  +------------------------------------------------------------+  |
|  | (amber) EN FILE D'ATTENTE                      il y a 1j   |  |
|  |                                                             |  |
|  | @charlie veut DERIVER votre PNJ Viktor                     |  |
|  |                                                             |  |
|  | "Je voudrais creer Lyra, inspiree de Viktor..."            |  |
|  |                                                             |  |
|  | (info) Sera traitable apres la demande precedente.         |  |
|  +------------------------------------------------------------+  |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Envoyees (1)                                                    |
|                                                                  |
|  +------------------------------------------------------------+  |
|  | (blue) EN ATTENTE                              il y a 3j   |  |
|  |                                                             |  |
|  | Vous voulez ADOPTER Fenris (PNJ de @dave)                  |  |
|  |                                                             |  |
|  | [Annuler ma demande]                                       |  |
|  +------------------------------------------------------------+  |
|                                                                  |
+------------------------------------------------------------------+
```

## Modal d'acceptation — US-11

```
+----------------------------------------------------------+
|                                                    [x]   |
|  Accepter la demande de @bob                             |
|                                                          |
|  @bob souhaite adopter Viktor.                           |
|                                                          |
|  Votre message de reponse (optionnel)                    |
|  {______________________________________________________}|
|  {  Un mot narratif pour accompagner                     }|
|  {  la transition...                                     }|
|  {______________________________________________________}|
|                                                          |
|  (info-circle) Une Sequence Partagee sera creee          |
|  pour co-ecrire la scene de transition.                  |
|                                                          |
|               [Confirmer l'acceptation]   Annuler        |
|                                                          |
+----------------------------------------------------------+
```

## SharedSequence (`/links/{id}/sequence/`) — US-18, US-19

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  Sequence Partagee                                               |
|  Viktor (PNJ) --> Adopt --> @bob                                |
|                                                                  |
|  Statut : (amber) Brouillon                                     |
|  Participants : @alice (createur) + @bob (adoptant)              |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Titre                                                           |
|  {_La rencontre au carrefour________________________________}    |
|                                                                  |
|  Contenu (Markdown collaboratif)                                 |
|  +------------------------------------------------------------+  |
|  | Viktor marchait sous la pluie quand une silhouette          |  |
|  | familiere apparut au bout de la ruelle.                     |  |
|  |                                                             |  |
|  | "Je te cherchais," dit l'inconnu.                          |  |
|  |                                                             |  |
|  | Viktor s'arreta. Il connaissait cette voix.                |  |
|  | C'etait celle de son passe.                                |  |
|  |                                                             |  |
|  |                                                             |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  Derniere modification par @alice, il y a 2h                     |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  [Sauvegarder]  [Proposer la publication]                        |
|                                                                  |
+------------------------------------------------------------------+
```

### Etat "Publication proposee"

```
+------------------------------------------------------------------+
|  (info) @alice propose de publier cette sequence.                |
|                                                                  |
|  [Valider et publier]   [Demander des modifications]             |
|                                                                  |
|  {Commentaire optionnel si modifications...___________________}  |
+------------------------------------------------------------------+
```

La publication requiert la validation des deux participants.

---

## File d'attente QUEUED — US-15

### Demande sur un PNJ qui a deja une demande PENDING

La modal d'Adopt/Claim/Fork affiche un avertissement supplementaire :

```
+----------------------------------------------------------+
|                                                    [x]   |
|  Adopter Viktor                                          |
|                                                          |
|  (alert-triangle) Viktor a deja 1 demande en attente.    |
|  Votre demande sera mise en file d'attente (QUEUED).     |
|  Vous serez notifie si elle devient traitable.            |
|                                                          |
|  Votre proposition narrative                              |
|  {______________________________________________________}|
|  {______________________________________________________}|
|                                                          |
|         [Envoyer (file d'attente)]   Annuler             |
|                                                          |
+----------------------------------------------------------+
```

### Carte de demande QUEUED (vue envoyees)

```
+------------------------------------------------------------+
| (gray) EN FILE D'ATTENTE (#2)                 il y a 3j   |
|                                                             |
| Vous voulez ADOPTER Viktor (PNJ de @alice)                 |
| Position dans la file : 2e                                  |
|                                                             |
| (info) Si la demande #1 est refusee, la votre passera     |
| automatiquement en attente de traitement.                   |
|                                                             |
| [Annuler ma demande]                                       |
+------------------------------------------------------------+
```

### Promotion automatique (notification)

Quand la demande precedente est refusee :

```
+------------------------------------------------------------+
| (bell) Votre demande d'Adopt sur Viktor est maintenant     |
| traitable ! @alice peut desormais examiner votre           |
| proposition.                                                |
+------------------------------------------------------------+
```

---

## Revocation de lien — US-16

### Revocation par le createur (avant publication SharedSequence)

Accessible depuis la fiche personnage (section "Lien actif") ou le dashboard GM.

```
+----------------------------------------------------------+
|                                                    [x]   |
|  Revoquer le lien avec Viktor                            |
|                                                          |
|  (alert) Viktor est actuellement adopte par @bob.        |
|  La Sequence Partagee est encore en brouillon.            |
|                                                          |
|  En revoquant :                                           |
|  - Le lien sera supprime                                  |
|  - Viktor redeviendra PNJ disponible                      |
|  - @bob sera notifie                                      |
|  - Le brouillon de la Sequence sera supprime              |
|                                                          |
|  Raison (envoyee a @bob)                                 |
|  {______________________________________________________}|
|  {______________________________________________________}|
|                                                          |
|           [Revoquer le lien]   Annuler                    |
|                                                          |
+----------------------------------------------------------+
```

### Revocation par le createur (apres publication)

```
+----------------------------------------------------------+
|                                                    [x]   |
|  Revoquer le lien avec Viktor                            |
|                                                          |
|  (alert) La Sequence Partagee "La rencontre au           |
|  carrefour" est deja publiee.                             |
|                                                          |
|  En revoquant :                                           |
|  - Le lien sera marque comme REVOQUE (pas supprime)       |
|  - Viktor redeviendra PNJ disponible                      |
|  - La Sequence restera visible avec mention               |
|    "lien revoque"                                         |
|  - @bob sera notifie                                      |
|                                                          |
|  Raison (envoyee a @bob)                                 |
|  {______________________________________________________}|
|                                                          |
|           [Revoquer le lien]   Annuler                    |
|                                                          |
+----------------------------------------------------------+
```

### Renonciation par l'adoptant

Accessible depuis la fiche du personnage adopte (section "Mon lien").

```
+----------------------------------------------------------+
|                                                    [x]   |
|  Renoncer a Viktor                                       |
|                                                          |
|  Vous abandonnez Viktor. Il redeviendra PNJ              |
|  disponible pour d'autres joueurs.                        |
|                                                          |
|  Message pour le createur (optionnel)                    |
|  {______________________________________________________}|
|                                                          |
|           [Confirmer la renonciation]   Annuler           |
|                                                          |
+----------------------------------------------------------+
```

### Badge REVOQUE sur fiche personnage

```
|  Statut : (red) Lien revoque                                     |
|  Ancien lien : Adopte par @bob (revoque le 10 mars 2026)        |
|  Sequence : "La rencontre au carrefour" (lien revoque)           |
|                                                                  |
|  (vert) Ce personnage est de nouveau disponible.                 |
|  [Adopter]  [Reclamer]  [Deriver]                                |
```

---

## Demande de lien cross-instance — US-23

### Modal Adopt cross-instance

Quand le PNJ est sur une instance distante, la modal ajoute des indicateurs :

```
+----------------------------------------------------------+
|                                                    [x]   |
|  Adopter Viktor                                          |
|  (globe) Instance distante : suddenly.games               |
|                                                          |
|  Vous souhaitez reprendre Viktor comme votre PJ.         |
|  La demande sera envoyee via ActivityPub a                |
|  @alice@suddenly.games                                    |
|                                                          |
|  Votre proposition narrative                              |
|  {______________________________________________________}|
|  {______________________________________________________}|
|                                                          |
|  (info-circle) Delai de reponse : si aucune reponse      |
|  sous 30 jours, la demande expirera automatiquement.      |
|                                                          |
|               [Envoyer la demande]   Annuler             |
|                                                          |
+----------------------------------------------------------+
```

### Carte de demande EXPIRED (vue envoyees)

```
+------------------------------------------------------------+
| (red) EXPIREE                                il y a 31j   |
|                                                             |
| Vous vouliez ADOPTER Viktor (PNJ de @alice@suddenly.games) |
| Aucune reponse recue dans les 30 jours.                    |
|                                                             |
| [Renvoyer la demande]  [Supprimer]                         |
+------------------------------------------------------------+
```

### SharedSequence cross-instance

```
+------------------------------------------------------------------+
|  Sequence Partagee                                               |
|  Viktor (PNJ) --> Adopt --> @bob                                |
|                                                                  |
|  (globe) Cross-instance : hebergee sur suddenly.games            |
|  Participants : @alice@suddenly.games + @bob (vous)              |
|                                                                  |
|  (info) L'editeur est heberge sur l'instance du createur.       |
|  Vos modifications sont synchronisees via ActivityPub.            |
+------------------------------------------------------------------+
```
