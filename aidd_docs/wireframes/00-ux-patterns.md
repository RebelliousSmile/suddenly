# 00 — Patterns UX transversaux

Patterns qui s'appliquent a travers tous les wireframes.
Issue de l'audit UX du 2026-04-05.

## 1. Etats vides

Chaque liste, section, ou page filtree DOIT avoir un etat vide avec :
- Une illustration ou icone contextuelle
- Un message explicatif
- Un call-to-action vers la prochaine etape logique

### Exemples

```
Profil — aucune partie :
+------------------------------------------------------------+
|  (book-open)                                                |
|  Vous n'avez pas encore de partie.                          |
|  [Creer ma premiere partie]                                 |
+------------------------------------------------------------+

Profil — aucun personnage :
+------------------------------------------------------------+
|  (users)                                                    |
|  Aucun personnage pour l'instant.                           |
|  Les personnages apparaitront quand vous les                |
|  mentionnerez dans un compte-rendu.                          |
+------------------------------------------------------------+

Recherche — aucun resultat :
+------------------------------------------------------------+
|  (search-x)                                                 |
|  Aucun resultat pour "xyz".                                 |
|  Essayez d'autres termes ou [explorez les PNJ disponibles] |
+------------------------------------------------------------+

Feed — fil vide :
+------------------------------------------------------------+
|  (rss)                                                      |
|  Votre fil est vide pour l'instant.                         |
|  [Suivez des joueurs] ou [explorez les parties]             |
|  pour voir du contenu ici.                                  |
+------------------------------------------------------------+

Dashboard GM — aucun PNJ :
+------------------------------------------------------------+
|  (users)                                                    |
|  Vous n'avez pas encore cree de PNJ.                        |
|  Les PNJ sont crees automatiquement quand vous              |
|  les mentionnez dans un compte-rendu.                        |
|  [Ecrire un compte-rendu]                                   |
+------------------------------------------------------------+
```

## 2. Confirmations et feedback

### Apres action reussie

Toute action destructive ou significative affiche un toast de confirmation :

```
Envoi de demande :
+------------------------------------------------------------+
| (check) Demande d'Adopt envoyee a @alice.                   |
|         Vous serez notifie de sa decision.                   |
+------------------------------------------------------------+

Revocation avec delai de grace :
+------------------------------------------------------------+
| (clock) Revocation programmee dans 24h.                     |
|         [Annuler la revocation]                              |
+------------------------------------------------------------+

Publication CR :
+------------------------------------------------------------+
| (check) Compte-rendu publie ! 3 personnages lies.           |
+------------------------------------------------------------+
```

### Sauvegarde automatique dans l'editeur

L'editeur de CR (`06-reports`) affiche un indicateur permanent :

```
+------------------------------------------------------------+
|  Contenu (Markdown)                    (cloud) Sauvegarde  |
|  +------------------------------------------------------+  |
|  | La nuit tombait...                                    |  |
|  +------------------------------------------------------+  |
|                                        (check) Sauvegarde  |
|                                  (spinner) Sauvegarde en   |
|                                            cours...        |
|                                  (alert) Non sauvegarde    |
```

## 3. Flow guide "Lier a mon histoire" (Adoption / Derivation / Retcon)

Remplace les 3 boutons Claim/Adopt/Fork par un **point d'entree unique**
[Lier a mon histoire] qui ouvre un flow guide en 2 etapes :

1. **Choix du type** : 3 cartes explicatives avec sous-titres narratifs
2. **Formulaire** : specifique au type choisi, avec bouton [<- Retour]

Voir `09-links.md` pour les wireframes detailles du flow.

**Terminologie narrative** (remplace le jargon technique) :

| Ancien | Nouveau | Sous-titre |
|--------|---------|-----------|
| Claim | **Retcon** | "C'etait mon PJ depuis le debut" |
| Adopt | **Adoption** | "Je reprends ce personnage" |
| Fork | **Derivation** | "Je cree un PJ inspire de lui" |

Le Retcon est presente en retrait (cas avance, tag "rare").

## 4. Indicateur de statut sur fiche personnage apres demande

Quand le joueur a une demande en cours sur un PNJ, la fiche
affiche un `@status_banner` et masque le bouton [Lier a mon histoire] :

```
+------------------------------------------------------------------+
|  @status_banner(type="info", icon="clock")                       |
|  Vous avez une demande d'Adoption en attente sur ce PNJ.        |
|  Envoyee il y a 2h.  [Voir ma demande]  [Annuler]               |
+------------------------------------------------------------------+
```

Ou si en file d'attente :

```
+------------------------------------------------------------------+
|  @status_banner(type="warning", icon="clock")                    |
|  Votre demande de Derivation est en file d'attente (#2).        |
|  [Voir ma demande]  [Annuler]                                    |
+------------------------------------------------------------------+
```

## 5. Filtres sur le fil d'actualite

Le fil (`10-feed`) doit permettre de filtrer par type :

```
|  Mon fil d'actualite                                             |
|                                                                  |
|  [Tout]  [Comptes-rendus]  [Sequences]  [PNJ]    <- onglets    |
```

## 6. Navigation vers le dashboard GM

Le header (`01-layout`) ajoute un lien conditionnel pour les GMs :

```
| (dice) Suddenly    Accueil  Explorer  Mes parties  Mes persos   |
|                                                                  |
|                    Dashboard*  (cloche)  [avatar v]              |
```

*Visible si l'utilisateur a cree au moins une partie.

## 7. Onboarding — bouton retour

Chaque etape de l'onboarding (`16-misc`) a un bouton retour :

```
|  [<- Retour]  Etape 2 de 3          [Passer l'introduction ->] |
```

## 8. Quote — modifier/supprimer

Les citations sur la fiche personnage (`08-quotes`) affichent un menu
contextuel pour l'auteur :

```
|  +------------------------------------------------------------+  |
|  |  |  "Les mythes ne meurent pas..."                         |  |
|  |  |                                                    ...  |  |
|  |  |  — Viktor, ajoutee par @alice            |              |  |
|  +------------------------------------------------------------+  |
                                                  |
                                                  v (dropdown, auteur seulement)
                                            +------------------+
                                            | (edit) Modifier  |
                                            | (trash) Supprimer|
                                            +------------------+
```

## 9. Indicateur de presence sur SharedSequence

L'editeur collaboratif (`09-links`) affiche la presence :

```
|  Participants :                                                  |
|  @alice (createur) (vert) en ligne                              |
|  @bob (adoptant)   (gris) vu il y a 3h                         |
```

## 10. Regroupement des settings

`15-settings` passe de 7 a 5 onglets :

```
|  > Profil                |
|    Compte et securite    |  <- fusion Compte + Securite
|    Langues               |
|    Notifications         |
|    Federation et donnees |  <- fusion Federation + Donnees
```

## 11. Force du mot de passe (signup)

`03-auth` signup ajoute un indicateur temps reel :

```
|  Mot de passe              |
|  {*****________________}   |
|  [====........] Moyen      |
|  Ajoutez des chiffres ou   |
|  symboles pour renforcer.  |
```
