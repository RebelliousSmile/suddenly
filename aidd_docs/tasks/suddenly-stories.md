# User Stories — Suddenly MVP

**Personas** :
- **Joueur solo** — documente ses parties et découvre que la plateforme est vivante
- **Game Master** — crée des PNJ via ses comptes-rendus et arbitre les demandes de lien
- **Admin d'instance** — modère le contenu et gère les relations avec les instances distantes

---

## Domaine 1 — Compte & Profil

### US-01: "Créer mon compte"

**As a** joueur solo
**I want** créer un compte sur une instance Suddenly
**So that** je dispose d'un espace pour documenter mes parties

```gherkin
Scenario: Inscription réussie
  Given je suis sur la page d'accueil
  When je m'inscris avec un courriel et un nom d'utilisateur
  Then mon profil public est créé et accessible via @utilisateur@instance
  And je peux configurer ma biographie et mon avatar
```

---

## Domaine 2 — Parties

### US-02: "Créer ma campagne"

**As a** joueur solo
**I want** créer une fiche de partie (titre, système de jeu, description)
**So that** mes comptes-rendus soient regroupés sous une campagne identifiable

```gherkin
Scenario: Création de partie
  Given je suis connecté
  When je crée une partie avec titre et système de jeu
  Then la partie apparaît dans mon profil avec son historique
  And la partie est publique et peut être suivie
```

### US-03: "Reconstituer une campagne passée"

**As a** joueur avec un historique de parties
**I want** créer une partie avec une date passée
**So that** j'archive mes campagnes sans perdre la chronologie

```gherkin
Scenario: Partie historique
  Given je crée une partie
  When je renseigne une date de début dans le passé
  Then les CRs peuvent avoir une date de session antérieure
  And la chronologie respecte la date de session, pas de publication
```

---

## Domaine 3 — Comptes-rendus

### US-04: "Écrire et publier un compte-rendu"

**As a** joueur solo
**I want** rédiger un CR en Markdown et le publier
**So that** mes sessions soient documentées et visibles par mes abonnés

```gherkin
Scenario: Publication de CR
  Given je suis dans une partie
  When je crée un CR avec titre et contenu Markdown
  Then le CR est publié, visible publiquement et fédéré
  And je peux sauvegarder un brouillon avant de publier
```

### US-05: "Mentionner des personnages dans un CR"

**As a** joueur solo
**I want** identifier des personnages dans mon CR pendant la rédaction
**So that** chaque personnage accumule un historique de ses apparitions

```gherkin
Scenario: Mention de personnage
  Given je rédige un CR
  When j'utilise le sélecteur de personnages
  Then le personnage est lié au CR et son historique est mis à jour
  And si le personnage n'existe pas, je peux le créer à la volée
```

---

## Domaine 4 — Personnages

### US-06: "Voir la fiche d'un personnage"

**As a** joueur solo
**I want** accéder à la fiche complète d'un personnage
**So that** je voie tout son historique narratif en un seul endroit

```gherkin
Scenario: Consultation de fiche
  Given je clique sur un personnage
  Then je vois son nom, description, avatar, statut et ses apparitions
  And je vois ses citations mémorables
  And si c'est un PNJ disponible, les boutons Adopter/Réclamer/Dériver sont visibles
```

### US-07: "Rechercher des personnages"

**As a** joueur solo
**I want** rechercher des personnages par nom ou système de jeu
**So that** je retrouve un personnage ou découvre des PNJ intéressants

```gherkin
Scenario: Recherche
  Given j'utilise la barre de recherche
  When je tape un nom ou système de jeu
  Then les personnages correspondants s'affichent avec statut et partie d'origine
  And les PNJ disponibles sont identifiés visuellement
```

---

## Domaine 5 — Citations

### US-08: "Ajouter une citation"

**As a** joueur solo
**I want** enregistrer une réplique mémorable d'un personnage
**So that** les moments forts de mes parties soient préservés

```gherkin
Scenario: Ajout de citation
  Given je suis sur la fiche d'un personnage ou dans un CR
  When j'ajoute une citation avec son contexte
  Then la citation apparaît sur la fiche du personnage et est fédérée si publique
  And je peux choisir Éphémère / Privée / Publique
```

---

## Domaine 6 — Liens (gameplay)

### US-09: "Être notifié d'une demande sur mon PNJ"

**As a** joueur qui a créé des PNJ
**I want** recevoir une notification quand quelqu'un veut Adopter/Réclamer/Dériver un PNJ
**So that** je découvre que mon PNJ a pris vie dans une autre histoire

```gherkin
Scenario: Notification de demande
  Given un joueur envoie une demande sur l'un de mes PNJ
  Then je reçois une notification avec demandeur, PNJ et proposition narrative
  And je peux lire la proposition avant d'accepter ou refuser
```

### US-10: "Envoyer une demande d'Adopt"

**As a** joueur qui a découvert un PNJ intéressant
**I want** envoyer une demande d'Adopt avec une proposition narrative
**So that** j'intègre ce personnage dans ma propre histoire

```gherkin
Scenario: Demande d'adoption
  Given je suis sur la fiche d'un PNJ disponible
  When je clique "Adopter" et rédige ma proposition narrative
  Then la demande est envoyée au créateur (via ActivityPub si cross-instance)
  And le PNJ passe en statut "En attente"
```

### US-11: "Accepter ou refuser une demande"

**As a** créateur d'un PNJ
**I want** accepter ou refuser une demande Claim/Adopt/Fork
**So that** je garde la maîtrise narrative de mes personnages

```gherkin
Scenario: Acceptation
  Given j'ai reçu une demande de lien
  When j'accepte
  Then un lien entre personnages est créé et le PNJ change de statut
  And une invitation à co-écrire la SharedSequence est envoyée aux deux joueurs

Scenario: Refus
  When je refuse
  Then le demandeur est notifié et le PNJ reste disponible
```

---

## Domaine 7 — Social & Fédération

### US-12: "Suivre une partie ou un joueur"

**As a** joueur solo
**I want** suivre la partie ou le profil d'un autre joueur (même sur une autre instance)
**So that** leurs nouveaux CRs apparaissent dans mon fil d'actualité

```gherkin
Scenario: Follow cross-instance
  Given je suis sur le profil d'un joueur ou une page de partie
  When je clique "Suivre"
  Then leurs publications apparaissent dans mon fil d'actualité
  And cela fonctionne même si le joueur est sur une autre instance
```

---

## Domaine 2b — Game Master

### US-13: "Planifier la distribution d'un compte-rendu"

**As a** Game Master
**I want** définir la liste des personnages (PJ/PNJ) qui apparaîtront dans mon CR avant de rédiger
**So that** l'interface me propose les mentions `@personnage` pendant la rédaction

```gherkin
Scenario: Distribution avec PNJ existants
  Given je rédige un CR dans une de mes parties
  When je définis la distribution (cast)
  Then je peux ajouter des personnages existants de ma partie
  And je peux créer de nouveaux PNJ à la volée (nom + description)

Scenario: Création de PNJ à la volée
  Given je définis la distribution
  When j'ajoute un personnage qui n'existe pas encore
  Then je renseigne un nom et une description minimale
  And le PNJ est créé à la publication du CR

Scenario: Rôles dans la distribution
  Given je définis la distribution
  When j'assigne un personnage
  Then je choisis son rôle : Principal / Secondaire / Mentionné
```

### US-14: "Arbitrer les demandes de lien sur mes PNJ"

**As a** Game Master
**I want** voir toutes les demandes en attente sur mes PNJ et les traiter une par une
**So that** je garde la maîtrise narrative de mes personnages

```gherkin
Scenario: Plusieurs demandes en file d'attente
  Given mon PNJ a reçu 3 demandes (Claim, Adopt, Fork)
  When je consulte les demandes
  Then elles sont affichées par ordre chronologique
  And je traite la première avant de voir la suivante

Scenario: Acceptation avec réponse narrative
  Given je reçois une demande d'Adopt
  When j'accepte
  Then je peux ajouter un message narratif de réponse
  And la SharedSequence est déclenchée

Scenario: Refus sans bloquer les suivantes
  Given je refuse la première demande de la file
  When la demande est rejetée
  Then le demandeur est notifié
  And la demande suivante dans la file devient traitable
```

---

## Domaine 6b — Liens (edge cases)

### US-15: "File d'attente sur un PNJ populaire"

**As a** joueur qui veut adopter un PNJ
**I want** envoyer ma demande même si d'autres sont en attente
**So that** ma proposition ne soit pas perdue si les précédentes sont refusées

```gherkin
Scenario: Demande ajoutée à la file
  Given un PNJ a déjà une demande PENDING
  When j'envoie une nouvelle demande
  Then ma demande est ajoutée à la file avec statut QUEUED
  And je suis notifié de ma position dans la file

Scenario: Promotion automatique
  Given ma demande est QUEUED et la demande précédente est refusée
  When le GM refuse la demande devant moi
  Then ma demande passe en PENDING
  And le GM est notifié de ma proposition

Scenario: Annulation volontaire
  Given ma demande est QUEUED
  When j'annule ma demande
  Then elle est retirée de la file
  And ma position est libérée pour les suivants
```

### US-16: "Révoquer un lien accepté"

**As a** créateur d'un PNJ dont le lien a été accepté
**I want** pouvoir révoquer le lien dans certaines conditions
**So that** je puisse corriger une erreur ou un abus

```gherkin
Scenario: Révocation avant publication de la SharedSequence
  Given un lien Adopt a été accepté mais la SharedSequence est encore en DRAFT
  When je révoque le lien
  Then le CharacterLink est supprimé
  And le PNJ revient en statut NPC
  And le demandeur est notifié

Scenario: Révocation après publication
  Given la SharedSequence est publiée
  When je révoque le lien
  Then le lien est marqué comme REVOKED (pas supprimé)
  And la SharedSequence reste visible avec mention "lien révoqué"
  And le PNJ revient en statut NPC

Scenario: Révocation côté demandeur
  Given je suis le joueur qui a adopté un PNJ
  When je souhaite abandonner le personnage
  Then je peux renoncer au lien
  And le PNJ revient disponible
```

### US-17: "Fork en chaîne"

**As a** joueur qui découvre un PJ issu d'un Fork
**I want** pouvoir forker ce personnage à mon tour
**So that** une lignée narrative se construise entre plusieurs joueurs

```gherkin
Scenario: Fork d'un personnage déjà forké
  Given un PJ "Lyra" est issue d'un Fork du PNJ "Viktor"
  When j'envoie une demande de Fork sur "Lyra"
  Then la demande est envoyée au propriétaire de "Lyra" (pas au créateur original)
  And le nouveau PJ aura "Lyra" comme parent dans sa lignée

Scenario: Affichage de la lignée
  Given un personnage a une chaîne de forks (Viktor → Lyra → mon PJ)
  When je consulte la fiche de mon PJ
  Then la lignée complète est visible (arbre de parenté)

Scenario: Pas de fork circulaire
  Given "Lyra" est un fork de "Viktor"
  When le propriétaire de "Viktor" tente de forker "Lyra"
  Then la demande est autorisée (pas de restriction circulaire)
```

---

## Domaine 8 — SharedSequence

### US-18: "Co-écrire une séquence partagée"

**As a** joueur dont la demande de lien a été acceptée
**I want** co-écrire une scène avec le créateur du PNJ en temps réel
**So that** notre connexion narrative soit scellée par un contenu commun

```gherkin
Scenario: Ouverture de l'éditeur collaboratif
  Given un lien a été accepté
  When les deux joueurs accèdent à la SharedSequence
  Then un éditeur collaboratif (type Etherpad) s'ouvre
  And les deux joueurs peuvent écrire simultanément en Markdown

Scenario: Édition asynchrone
  Given un joueur a commencé à écrire
  When l'autre joueur se connecte plus tard
  Then il voit le texte déjà écrit et peut continuer
  And l'historique des modifications est visible

Scenario: Séquence cross-instance
  Given le lien est entre deux joueurs d'instances différentes
  When ils accèdent à la SharedSequence
  Then l'éditeur est hébergé sur l'instance du créateur du PNJ
  And l'autre joueur y accède via son compte fédéré
```

### US-19: "Valider et publier la séquence partagée"

**As a** l'un des deux joueurs d'une SharedSequence
**I want** proposer la publication quand la scène est terminée
**So that** le contenu devienne canonique et visible publiquement

```gherkin
Scenario: Double validation requise
  Given la scène est rédigée
  When un joueur clique "Proposer la publication"
  Then l'autre joueur reçoit une notification
  And la publication n'a lieu que si les deux valident

Scenario: Demande de modification
  Given un joueur propose la publication
  When l'autre joueur refuse
  Then il peut ajouter un commentaire expliquant ce qu'il faut changer
  And l'éditeur reste ouvert

Scenario: Publication
  Given les deux joueurs ont validé
  When la SharedSequence est publiée
  Then elle apparaît dans l'historique des deux personnages
  And elle est fédérée si les deux joueurs sont sur des instances différentes
```

---

## Domaine 9 — Notifications

### US-20: "Recevoir des notifications in-app"

**As a** joueur
**I want** voir mes notifications dans un fil dédié
**So that** je ne manque aucune interaction sur mes personnages ou parties

```gherkin
Scenario: Types de notifications
  Given je suis connecté
  When je consulte mon fil de notifications
  Then je vois les notifications groupées par type :
    | Type | Déclencheur |
    | Demande de lien | Quelqu'un veut Claim/Adopt/Fork mon PNJ |
    | Réponse à ma demande | Ma demande acceptée/refusée |
    | SharedSequence | Invitation à co-écrire, proposition de publication |
    | Nouveau CR | Un joueur/partie que je suis a publié |
    | Nouveau follower | Quelqu'un me suit |

Scenario: Marquage lu/non-lu
  Given j'ai des notifications non lues
  When je clique sur une notification
  Then elle est marquée comme lue
  And je peux marquer toutes comme lues en un clic

Scenario: Badge de compteur
  Given j'ai 3 notifications non lues
  When je navigue sur le site
  Then un badge "3" est visible sur l'icône notifications
```

### US-21: "Configurer mes préférences de notification"

**As a** joueur
**I want** choisir quels types de notifications m'envoient un email ou un push
**So that** je ne sois pas submergé mais ne manque pas l'essentiel

```gherkin
Scenario: Paramétrage par canal
  Given je suis dans mes paramètres
  When je configure mes notifications
  Then je peux activer/désactiver par type ET par canal (in-app / email / push)
  And les notifications in-app sont toujours actives (non désactivables)

Scenario: Valeurs par défaut
  Given je crée mon compte
  Then les notifications in-app sont activées pour tout
  And les emails sont activés pour : demandes de lien, réponses, SharedSequence
  And les push sont désactivés par défaut
```

---

## Domaine 10 — Fédération cross-instance

### US-22: "Suivre un joueur ou une partie sur une autre instance"

**As a** joueur sur instance A
**I want** suivre un joueur ou une partie sur instance B
**So that** ses publications apparaissent dans mon fil d'actualité

```gherkin
Scenario: Recherche fédérée
  Given je connais l'identifiant @joueur@instance-b.social
  When je le recherche sur mon instance
  Then son profil distant s'affiche avec ses parties et personnages publics
  And je peux cliquer "Suivre"

Scenario: Réception de contenu fédéré
  Given je suis un joueur sur une instance distante
  When il publie un nouveau CR
  Then le CR apparaît dans mon fil d'actualité
  And je peux lire le contenu complet depuis mon instance
```

### US-23: "Envoyer une demande de lien cross-instance"

**As a** joueur sur instance A
**I want** envoyer une demande Adopt/Claim/Fork sur un PNJ hébergé sur instance B
**So that** les liens narratifs ne soient pas limités à une seule instance

```gherkin
Scenario: Adopt cross-instance
  Given je suis sur la fiche d'un PNJ distant
  When je clique "Adopter" et rédige ma proposition
  Then la demande est envoyée via ActivityPub (Offer) à l'instance distante
  And le créateur du PNJ est notifié sur son instance

Scenario: Acceptation cross-instance
  Given le créateur distant accepte ma demande
  When l'Accept activity arrive sur mon instance
  Then le lien est créé sur les deux instances
  And la SharedSequence est initiée (hébergée sur l'instance du PNJ)

Scenario: Timeout
  Given j'ai envoyé une demande à une instance distante
  When l'instance ne répond pas dans les 30 jours
  Then ma demande passe en statut EXPIRED
  And je suis notifié
```

### US-24: "Voir le contenu Suddenly depuis Mastodon"

**As a** utilisateur Mastodon
**I want** voir les publications Suddenly dans mon fil quand je suis un joueur
**So that** je découvre les comptes-rendus sans créer de compte Suddenly

```gherkin
Scenario: CR visible comme Article
  Given je suis un joueur Suddenly depuis Mastodon
  When le joueur publie un CR
  Then il apparaît comme un Article dans mon fil Mastodon
  And je peux lire le contenu et voir le lien vers la source

Scenario: Citation visible comme Note
  Given je suis un personnage Suddenly depuis Mastodon
  When une citation publique est ajoutée
  Then elle apparaît comme une Note dans mon fil

Scenario: Activités Suddenly-only
  Given une Offer (Claim/Adopt/Fork) est émise
  Then elle n'est PAS envoyée aux instances non-Suddenly
  And seules les instances Suddenly la reçoivent
```

---

## Domaine 11 — Administration

### US-25: "Modérer le contenu de mon instance"

**As a** admin d'instance
**I want** pouvoir supprimer du contenu et suspendre des comptes
**So that** mon instance reste un espace sain pour les joueurs

```gherkin
Scenario: Suppression de contenu
  Given un CR ou une citation est signalé
  When je le supprime en tant qu'admin
  Then le contenu est masqué (soft delete)
  And l'auteur est notifié avec la raison

Scenario: Suspension de compte
  Given un utilisateur a des comportements abusifs
  When je suspends son compte
  Then ses publications sont masquées
  And il ne peut plus se connecter
  And ses followers distants reçoivent un Delete activity

Scenario: Avertissement
  Given un contenu est problématique mais pas grave
  When j'envoie un avertissement
  Then l'utilisateur reçoit un message admin
  And l'incident est consigné dans le journal de modération
```

### US-26: "Bloquer ou limiter une instance distante"

**As a** admin d'instance
**I want** bloquer ou limiter les interactions avec une instance distante
**So that** je protège mes utilisateurs du spam ou contenu inapproprié

```gherkin
Scenario: Blocage complet
  Given une instance distante envoie du spam
  When je la bloque
  Then toutes les activités entrantes sont rejetées
  And les contenus existants de cette instance sont masqués
  And mes utilisateurs ne peuvent plus interagir avec cette instance

Scenario: Limitation (silence)
  Given une instance a du contenu de qualité variable
  When je la limite
  Then ses contenus n'apparaissent plus dans les fils publics
  And les utilisateurs qui suivent explicitement des joueurs de cette instance continuent à les voir

Scenario: Déblocage
  Given j'ai bloqué une instance par erreur
  When je la débloque
  Then les interactions reprennent normalement
  And les contenus masqués redeviennent visibles
```

### US-27: "Signaler un contenu"

**As a** joueur
**I want** signaler un contenu ou un comportement inapproprié
**So that** l'admin de mon instance puisse agir

```gherkin
Scenario: Signalement avec catégorie
  Given je vois un contenu problématique
  When je clique "Signaler"
  Then je choisis une catégorie (spam, harcèlement, contenu inapproprié, autre)
  And je peux ajouter un commentaire
  And le signalement est envoyé à l'admin de mon instance

Scenario: Signalement cross-instance
  Given le contenu signalé vient d'une instance distante
  When je signale
  Then le signalement est envoyé à l'admin de MON instance
  And l'admin peut transférer le signalement à l'instance distante (Flag activity)
```

---

## Priorité d'implémentation

| Priorité | US | Domaine | Justification |
|----------|-----|---------|---------------|
| 1 | US-01 | Compte & Profil | Prérequis absolu |
| 2 | US-02, US-03 | Parties | Contenant des CRs |
| 2 | US-13 | GM — Distribution | Prérequis pour la rédaction de CRs |
| 3 | US-04, US-05 | Comptes-rendus | Valeur principale |
| 4 | US-06, US-07 | Personnages | Découle des CRs |
| 5 | US-08 | Citations | Gain immédiat, haute valeur perçue |
| 5 | US-20, US-21 | Notifications | Nécessaire dès que les interactions existent |
| 6 | US-09, US-10, US-11 | Liens (base) | Le gameplay — arrive quand la base existe |
| 6 | US-14 | GM — Arbitrage | Prérequis pour le workflow de liens |
| 6 | US-15, US-16, US-17 | Liens (edge cases) | Robustesse du gameplay |
| 6 | US-18, US-19 | SharedSequence | Cœur du gameplay de lien |
| 7 | US-12, US-22 | Social & Follow | Amplifie la valeur existante |
| 7 | US-23 | Lien cross-instance | Fédération gameplay |
| 7 | US-24 | Compatibilité Mastodon | Visibilité externe |
| 7 | US-25, US-26, US-27 | Administration | Gouvernance d'instance |
