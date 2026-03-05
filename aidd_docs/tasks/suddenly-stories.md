# User Stories — Suddenly MVP

**Persona principale** : Joueur solo qui documente ses parties et découvre que la plateforme est vivante.

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

## Priorité d'implémentation

| Priorité | Domaine | Justification |
|----------|---------|---------------|
| 1 | Compte & Profil | Prérequis absolu |
| 2 | Parties | Contenant des CRs |
| 3 | Comptes-rendus | Valeur principale |
| 4 | Personnages | Découle des CRs |
| 5 | Citations | Gain immédiat, haute valeur perçue |
| 6 | Liens | Le gameplay — arrive quand la base existe |
| 7 | Social & Fédération | Amplifie la valeur existante |
