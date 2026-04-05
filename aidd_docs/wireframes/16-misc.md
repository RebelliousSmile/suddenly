# 16 — Onboarding, signalement, pages d'erreur

## Onboarding — premier login

Affiche apres la premiere connexion (signup). Aide le joueur a demarrer.

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|  Bienvenue sur Suddenly, {username} !                            |
|                                                                  |
|  Etape 1 de 3                    [Passer l'introduction ->]      |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  Completez votre profil                                          |
|                                                                  |
|  Nom d'affichage                                                 |
|  {______________________________}                                |
|                                                                  |
|  Biographie (optionnel)                                          |
|  {______________________________}                                |
|  {______________________________}                                |
|                                                                  |
|  Avatar (optionnel)                                              |
|  +----------------------+                                        |
|  | (upload) Choisir     |                                        |
|  +----------------------+                                        |
|                                                                  |
|                              [Continuer ->]                      |
|                                                                  |
+------------------------------------------------------------------+
```

### Etape 2 — Decouverte

```
+------------------------------------------------------------------+
|  Etape 2 de 3                    [Passer l'introduction ->]      |
+------------------------------------------------------------------+
|                                                                  |
|  Decouvrez votre instance                                        |
|                                                                  |
|  +------------------------------------------------------------+  |
|  | Vous migrez d'une autre instance ?                          |  |
|  | [Importer mes follows (CSV)]                                |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  Apercu de l'activite locale                                     |
|                                                                  |
|  @feed_item — dernier CR public local                            |
|  @feed_item — avant-dernier CR public local                      |
|                                                                  |
|  Joueurs actifs sur cette instance                               |
|                                                                  |
|  +------+ @alice  ·  12 parties  ·  [Suivre]                    |
|  +------+ @bob    ·   8 parties  ·  [Suivre]                    |
|  +------+ @charlie · 5 parties   ·  [Suivre]                    |
|  +------+ @dave   ·   3 parties  ·  [Suivre]                    |
|                                                                  |
|  Parties populaires                                              |
|                                                                  |
|  @game_card (compact) [Suivre]                                   |
|  @game_card (compact) [Suivre]                                   |
|  @game_card (compact) [Suivre]                                   |
|                                                                  |
|                              [Continuer ->]                      |
|                                                                  |
+------------------------------------------------------------------+
```

### Etape 3 — Premiere action

```
+------------------------------------------------------------------+
|  Etape 3 de 3                                                    |
+------------------------------------------------------------------+
|                                                                  |
|  Que voulez-vous faire en premier ?                              |
|                                                                  |
|  +---------------------------+  +---------------------------+    |
|  | (book-open)               |  | (search)                  |    |
|  |                           |  |                           |    |
|  | Creer ma premiere         |  | Explorer les              |    |
|  | partie                    |  | personnages               |    |
|  |                           |  |                           |    |
|  | Commencez a documenter    |  | Decouvrez les PNJ        |    |
|  | vos sessions de JDR       |  | d'autres joueurs          |    |
|  |                           |  |                           |    |
|  | [Creer une partie ->]    |  | [Explorer ->]             |    |
|  +---------------------------+  +---------------------------+    |
|                                                                  |
|  +---------------------------+                                   |
|  | (rss)                     |                                   |
|  |                           |                                   |
|  | Voir mon fil              |                                   |
|  | d'actualite               |                                   |
|  |                           |                                   |
|  | Suivez les publications   |                                   |
|  | de la communaute          |                                   |
|  |                           |                                   |
|  | [Aller au fil ->]        |                                   |
|  +---------------------------+                                   |
|                                                                  |
+------------------------------------------------------------------+
```

---

## Modal de signalement — US-27

Accessible depuis tout contenu via un bouton `(flag)` dans le menu contextuel
(report card, quote card, profil, fiche personnage).

### Bouton declencheur (dans les cartes)

```
|  (heart) 4  (message) 2  (share)  ... |
                                      |
                                      v (dropdown)
                                +------------------+
                                | Copier le lien   |
                                | ──────────────── |
                                | (flag) Signaler  |
                                +------------------+
```

### Modal de signalement

```
+----------------------------------------------------------+
|                                                    [x]   |
|  Signaler ce contenu                                     |
|                                                          |
|  CR "Session 8" par @troll123                            |
|                                                          |
|  Categorie                                               |
|  ( ) Spam                                                |
|  ( ) Harcelement                                         |
|  ( ) Contenu inapproprie                                 |
|  ( ) Autre                                               |
|                                                          |
|  Commentaire (optionnel)                                 |
|  {______________________________________________________}|
|  {______________________________________________________}|
|                                                          |
|  (info) Le signalement sera envoye a l'admin de          |
|  votre instance. Si le contenu provient d'une            |
|  instance distante, l'admin pourra transmettre           |
|  le signalement.                                         |
|                                                          |
|               [Envoyer le signalement]   Annuler         |
|                                                          |
+----------------------------------------------------------+
```

### Confirmation apres signalement

```
+----------------------------------------------------------+
|  (check-circle) Signalement envoye.                      |
|                                                          |
|  L'equipe de moderation examinera votre signalement.     |
|  Vous serez notifie de la decision.                      |
|                                                          |
|                                              [Fermer]    |
+----------------------------------------------------------+
```

---

## Pages d'erreur

### 404 — Page non trouvee

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|                                                                  |
|                     (search-x)                                   |
|                                                                  |
|                  Page non trouvee                                 |
|                                                                  |
|          Le personnage que vous cherchez a peut-etre              |
|          change d'histoire.                                      |
|                                                                  |
|          [Retour a l'accueil]   [Explorer]                       |
|                                                                  |
|                                                                  |
+------------------------------------------------------------------+
|                         FOOTER                                   |
+------------------------------------------------------------------+
```

### 403 — Acces refuse

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|                     (shield-x)                                   |
|                                                                  |
|                  Acces refuse                                    |
|                                                                  |
|          Vous n'avez pas les droits pour                         |
|          acceder a cette page.                                   |
|                                                                  |
|          [Retour a l'accueil]   [Se connecter]                   |
|                                                                  |
+------------------------------------------------------------------+
```

### 500 — Erreur serveur

```
+------------------------------------------------------------------+
|                         HEADER                                   |
+------------------------------------------------------------------+
|                                                                  |
|                     (alert-triangle)                             |
|                                                                  |
|                  Oups, quelque chose                              |
|                  s'est mal passe                                 |
|                                                                  |
|          L'equipe a ete notifiee. Reessayez                     |
|          dans quelques instants.                                 |
|                                                                  |
|          [Retour a l'accueil]   [Recharger]                     |
|                                                                  |
+------------------------------------------------------------------+
```

---

## Confirmation de suppression generique

Modal reutilisable pour supprimer un CR, une citation, une partie, etc.

```
+----------------------------------------------------------+
|                                                    [x]   |
|  Supprimer ce compte-rendu ?                             |
|                                                          |
|  "Session 12 : L'Oracle brise"                           |
|                                                          |
|  (alert) Cette action est irreversible.                  |
|  Le contenu sera supprime et les mentions                |
|  de personnages seront retirees.                         |
|                                                          |
|            [Supprimer]   Annuler                          |
|                                                          |
+----------------------------------------------------------+
```
