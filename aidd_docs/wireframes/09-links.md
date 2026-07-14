# 09 — Liens narratifs (Adoption / Derivation / Retcon)

## Terminologie

| Ancien terme | Nouveau terme | Sous-titre | Icone |
|-------------|--------------|-----------|-------|
| Adopt | **Adoption** | "Je reprends ce personnage" | `i-lucide-heart` |
| Fork | **Derivation** | "Je cree un PJ inspire de lui" | `i-lucide-git-branch` |
| Claim | **Retcon** | "C'etait mon PJ depuis le debut" | `i-lucide-git-merge` |

---

## Flow guide — "Lier a mon histoire" — US-10

Declenchee par le bouton unique [Lier a mon histoire] sur la fiche PNJ.
Utilise `@modal` (Alpine.js). Le flow a 2 etapes : choix du type, puis formulaire.

### Etape 1 — Choix du type de lien

```
+----------------------------------------------------------+
|                                                    [x]   |
|  Comment voulez-vous lier Viktor a votre histoire ?      |
|                                                          |
|  +----------------------------------------------------+  |
|  | (heart) Adoption                                    |  |
|  |                                                     |  |
|  | Viktor devient VOTRE PJ. Il quitte son ancienne     |  |
|  | histoire pour rejoindre la votre. Le createur        |  |
|  | devra accepter.                                      |  |
|  |                                                     |  |
|  |                                     [Choisir ->]    |  |
|  +----------------------------------------------------+  |
|                                                          |
|  +----------------------------------------------------+  |
|  | (git-branch) Derivation                             |  |
|  |                                                     |  |
|  | Vous creez un NOUVEAU PJ inspire de Viktor.          |  |
|  | Viktor reste disponible pour d'autres joueurs.       |  |
|  | Vos deux personnages seront lies par une lignee.     |  |
|  |                                                     |  |
|  |                                     [Choisir ->]    |  |
|  +----------------------------------------------------+  |
|                                                          |
|  +----------------------------------------------------+  |
|  | (git-merge) Retcon                          (rare)  |  |
|  |                                                     |  |
|  | Reecriture retroactive : Viktor etait en fait       |  |
|  | votre PJ depuis le debut. Son histoire est          |  |
|  | reinterpretee.                                       |  |
|  |                                                     |  |
|  |                                     [Choisir ->]    |  |
|  +----------------------------------------------------+  |
|                                                          |
+----------------------------------------------------------+
```

L'option Retcon est visuellement en retrait (bordure grise, pas de couleur)
avec un tag "(rare)" pour indiquer que c'est un cas d'usage avance.

### Etape 2a — Formulaire Adoption

```
+----------------------------------------------------------+
|  [<- Retour]                                       [x]   |
|                                                          |
|  Adopter Viktor                                          |
|  (heart) Adoption                                        |
|                                                          |
|  Vous souhaitez reprendre Viktor comme votre PJ.         |
|  @alice devra accepter votre demande.                    |
|                                                          |
|  Votre proposition narrative                              |
|  {______________________________________________________}|
|  {  Expliquez comment Viktor s'integre dans votre        }|
|  {  histoire et pourquoi ce lien vous interesse...       }|
|  {______________________________________________________}|
|                                                          |
|  (info) Apres acceptation, vous co-ecrirez une           |
|  Sequence Partagee avec @alice pour sceller la            |
|  transition narrative.                                    |
|                                                          |
|               [Envoyer la demande]   Annuler             |
|                                                          |
+----------------------------------------------------------+
```

### Etape 2b — Formulaire Derivation

```
+----------------------------------------------------------+
|  [<- Retour]                                       [x]   |
|                                                          |
|  Deriver Viktor                                          |
|  (git-branch) Derivation                                 |
|                                                          |
|  Vous creez un nouveau PJ inspire de Viktor.             |
|  Viktor reste PNJ — votre PJ sera lie par une            |
|  lignee narrative.                                        |
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

### Etape 2c — Formulaire Retcon

```
+----------------------------------------------------------+
|  [<- Retour]                                       [x]   |
|                                                          |
|  Retcon sur Viktor                                       |
|  (git-merge) Retcon                                      |
|                                                          |
|  Vous affirmez que Viktor etait votre PJ depuis le       |
|  debut. Son histoire sera reinterpretee.                  |
|                                                          |
|  Votre personnage existant (optionnel)                   |
|  {Rechercher un de vos PJ...______________________}      |
|  hx-get="/htmx/characters/suggest/?owner=me"             |
|                                                          |
|  Votre explication narrative                              |
|  {______________________________________________________}|
|  {______________________________________________________}|
|                                                          |
|               [Envoyer la demande]   Annuler             |
|                                                          |
+----------------------------------------------------------+
```

### Confirmation apres envoi

```
+----------------------------------------------------------+
|                                                          |
|  (check-circle) Demande envoyee !                        |
|                                                          |
|  Votre demande d'Adoption a ete envoyee a @alice.        |
|  Vous serez notifie de sa decision.                      |
|                                                          |
|  [Voir ma demande]   [Fermer]                            |
|                                                          |
+----------------------------------------------------------+
```

La fiche PNJ affiche maintenant le `@status_banner` de demande en cours
et masque le bouton [Lier a mon histoire].

---

## Avertissement file d'attente — US-15

Si le PNJ a deja une demande PENDING, l'avertissement apparait
**avant l'etape 1** :

```
+----------------------------------------------------------+
|                                                    [x]   |
|                                                          |
|  @status_banner(type="warning", icon="alert-triangle")   |
|  Viktor a deja 1 demande en attente de traitement.       |
|  Votre demande sera mise en file d'attente (QUEUED).     |
|  Vous serez notifie si elle devient traitable.            |
|                                                          |
|  Comment voulez-vous lier Viktor a votre histoire ?      |
|  (suite du flow guide etape 1)                            |
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

---

## Page de gestion des demandes (`/requests/`) — US-09, US-11, US-14

Accessible depuis le header (icone liens + badge) ou le profil.

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  Demandes de lien                                                |
|                                                                  |
|  [Recues | Envoyees]       Filtre: [Toutes v]                    |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Recues (3)                                                      |
|                                                                  |
|  @link_request_card(request=req1, perspective="received")        |
|  — @bob veut ADOPTER Viktor — il y a 2h — [Accepter] [Refuser] |
|                                                                  |
|  @link_request_card(request=req2, perspective="received")        |
|  — @charlie veut DERIVER Viktor — il y a 1j — (en file)        |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Envoyees (1)                                                    |
|                                                                  |
|  @link_request_card(request=req3, perspective="sent")            |
|  — Vous voulez ADOPTER Fenris — il y a 3j — [Annuler]          |
|                                                                  |
+------------------------------------------------------------------+
```

---

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
|  (info) Une Sequence Partagee sera creee pour             |
|  co-ecrire la scene de transition.                        |
|                                                          |
|               [Confirmer l'acceptation]   Annuler        |
|                                                          |
+----------------------------------------------------------+
```

### Confirmation post-acceptation (CTA vers SharedSequence)

```
+----------------------------------------------------------+
|                                                          |
|  (check-circle) Demande acceptee !                       |
|                                                          |
|  Viktor est maintenant le PJ de @bob.                    |
|  Une Sequence Partagee a ete creee pour vous deux.       |
|                                                          |
|  [Ouvrir la Sequence Partagee ->]   [Plus tard]          |
|                                                          |
+----------------------------------------------------------+
```

Le demandeur recoit une notification avec le meme CTA :

```
+------------------------------------------------------------+
| (check) @alice a accepte votre demande d'Adoption          |
| sur Viktor ! [Ouvrir la Sequence Partagee ->]              |
+------------------------------------------------------------+
```

---

## Revocation de lien — US-16

### Revocation par le createur (avant publication SharedSequence)

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

---

## Demande cross-instance — US-23

Quand le PNJ est distant, le flow guide ajoute un indicateur a l'etape 1 :

```
|  (globe) Viktor est sur suddenly.games                   |
|  La demande sera envoyee via ActivityPub.                 |
|  Delai : si aucune reponse sous 30 jours, la demande     |
|  expirera automatiquement.                                |
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

---

## SharedSequence (`/links/{id}/sequence/`) — US-18, US-19

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  Sequence Partagee                                               |
|  Viktor (PNJ) --> Adoption --> @bob                             |
|                                                                  |
|  Statut : (warning) Brouillon                                   |
|  @presence_indicator(participants=...)                            |
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
|  @status_banner(type="info", icon="send")                        |
|  @alice propose de publier cette sequence.                       |
|                                                                  |
|  [Valider et publier]   [Demander des modifications]             |
|                                                                  |
|  {Commentaire optionnel si modifications...___________________}  |
+------------------------------------------------------------------+
```

La publication requiert la validation des deux participants.

### SharedSequence cross-instance

```
+------------------------------------------------------------------+
|  @status_banner(type="info", icon="globe")                       |
|  Cross-instance : hebergee sur suddenly.games                    |
|  Vos modifications sont synchronisees via ActivityPub.            |
+------------------------------------------------------------------+
```
