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
