# User Stories — Suddenly MVP

**Persona** : Joueur solo qui utilise Suddenly comme journal de campagne intelligent, et découvre que la plateforme est vivante. Peut arriver avec ou sans historique de parties. Son contenu est public par défaut. Le gameplay bonus (Claim/Adopt/Fork) se révèle naturellement quand la base existe — c'est aussi le parcours de Bob, joueur distant qui documente ses propres parties avant de découvrir des PNJ sur d'autres instances.

---

## Domaine 1 — Compte & Profil

### "Créer mon compte"

**En tant que** joueur solo
**Je veux** créer un compte sur une instance Suddenly
**Afin de** disposer d'un espace personnel pour documenter mes parties

- Critères d'acceptation :
  - [ ] Étant donné : je suis sur la page d'accueil
  - [ ] Quand : je m'inscris avec un courriel et un nom d'utilisateur
  - [ ] Alors : mon profil public est créé et accessible via `@utilisateur@instance`
  - [ ] Et : je peux configurer ma biographie et mon avatar

---

## Domaine 2 — Parties

### "Créer ma campagne"

**En tant que** joueur solo
**Je veux** créer une fiche de partie (titre, système de jeu, description)
**Afin que** mes comptes-rendus soient regroupés sous une campagne identifiable

- Critères d'acceptation :
  - [ ] Étant donné : je suis connecté
  - [ ] Quand : je crée une partie avec un titre et un système de jeu
  - [ ] Alors : la partie apparaît dans mon profil avec son historique de comptes-rendus
  - [ ] Et : la partie est publique et peut être suivie par d'autres joueurs

### "Reconstituer une campagne passée"

**En tant que** joueur avec un historique de parties
**Je veux** créer une partie avec une date de début dans le passé et y ajouter des comptes-rendus antérieurs
**Afin de** archiver mes campagnes passées sans perdre la chronologie

- Critères d'acceptation :
  - [ ] Étant donné : je crée une partie
  - [ ] Quand : je renseigne une date de début antérieure à aujourd'hui
  - [ ] Alors : les comptes-rendus de cette partie peuvent avoir une date de session dans le passé
  - [ ] Et : la chronologie du fil d'actualité respecte la date de session, pas la date de publication

---

## Domaine 3 — Comptes-rendus

### "Écrire et publier un compte-rendu"

**En tant que** joueur solo
**Je veux** rédiger un compte-rendu en Markdown et le publier
**Afin que** mes sessions soient documentées et lisibles par mes abonnés

- Critères d'acceptation :
  - [ ] Étant donné : je suis dans une partie
  - [ ] Quand : je crée un nouveau compte-rendu avec un titre et un contenu Markdown
  - [ ] Alors : le compte-rendu est publié, visible publiquement, et fédéré vers mes abonnés
  - [ ] Et : je peux sauvegarder un brouillon avant de publier

### "Mentionner des personnages dans un compte-rendu"

**En tant que** joueur solo
**Je veux** identifier des personnages dans mon compte-rendu pendant la rédaction
**Afin que** chaque personnage accumule un historique de ses apparitions

- Critères d'acceptation :
  - [ ] Étant donné : je rédige un compte-rendu
  - [ ] Quand : j'utilise le sélecteur de personnages
  - [ ] Alors : le personnage est lié au compte-rendu et son historique est mis à jour
  - [ ] Et : si le personnage n'existe pas encore, je peux le créer à la volée avec un nom et une description

### "Voir les suggestions de personnages"

**En tant que** joueur solo
**Je veux** recevoir des suggestions de personnages existants quand j'en mentionne un dans mon compte-rendu
**Afin de** ne pas créer de doublons et maintenir une base de personnages cohérente

- Critères d'acceptation :
  - [ ] Étant donné : je tape un nom de personnage dans mon compte-rendu
  - [ ] Quand : ce nom ressemble à un personnage existant dans ma base
  - [ ] Alors : une suggestion apparaît avec le nom, l'avatar et la partie d'origine
  - [ ] Et : je peux ignorer la suggestion et créer un nouveau personnage

---

## Domaine 4 — Personnages

### "Voir la fiche d'un personnage"

**En tant que** joueur solo
**Je veux** accéder à la fiche complète d'un personnage
**Afin de** voir tout son historique narratif en un seul endroit

- Critères d'acceptation :
  - [ ] Étant donné : je clique sur un personnage
  - [ ] Alors : je vois son nom, description, avatar, statut (PNJ/PJ) et la liste de ses apparitions dans les comptes-rendus
  - [ ] Et : je vois ses citations mémorables
  - [ ] Et : si le personnage est un PNJ disponible, un bouton "Adopter / Réclamer / Dériver" est visible

### "Rechercher des personnages"

**En tant que** joueur solo
**Je veux** rechercher des personnages par nom ou système de jeu
**Afin de** retrouver un personnage spécifique ou découvrir des PNJ intéressants

- Critères d'acceptation :
  - [ ] Étant donné : j'utilise la barre de recherche
  - [ ] Quand : je tape un nom ou un système de jeu
  - [ ] Alors : les personnages correspondants s'affichent avec leur statut et leur partie d'origine
  - [ ] Et : les PNJ disponibles (non encore adoptés) sont identifiés visuellement

---

## Domaine 5 — Citations

### "Ajouter une citation à un personnage"

**En tant que** joueur solo
**Je veux** enregistrer une réplique mémorable d'un personnage pendant ou après une session
**Afin que** les moments forts de mes parties soient préservés

- Critères d'acceptation :
  - [ ] Étant donné : je suis sur la fiche d'un personnage ou dans un compte-rendu
  - [ ] Quand : j'ajoute une citation avec son contexte
  - [ ] Alors : la citation apparaît sur la fiche du personnage et est fédérée (si publique)
  - [ ] Et : je peux choisir entre Éphémère (non fédérée), Privée ou Publique

---

## Domaine 6 — Liens (gameplay)

### "Être notifié qu'un PNJ intéresse quelqu'un"

**En tant que** joueur qui a créé des PNJ
**Je veux** recevoir une notification quand quelqu'un souhaite Adopter, Réclamer ou Dériver un de mes PNJ
**Afin de** découvrir que mon PNJ a pris vie dans une autre histoire

- Critères d'acceptation :
  - [ ] Étant donné : un autre joueur envoie une demande sur l'un de mes PNJ
  - [ ] Alors : je reçois une notification avec le nom du demandeur, le PNJ concerné et sa proposition narrative
  - [ ] Et : je peux lire la proposition avant d'accepter ou de refuser

### "Accepter ou refuser une demande de lien"

**En tant que** créateur d'un PNJ
**Je veux** accepter ou refuser une demande Claim/Adopt/Fork
**Afin de** garder la maîtrise narrative de mes personnages

- Critères d'acceptation :
  - [ ] Étant donné : j'ai reçu une demande de lien
  - [ ] Quand : j'accepte
  - [ ] Alors : un lien entre personnages est créé et le PNJ change de statut (ADOPTÉ/RÉCLAMÉ/DÉRIVÉ)
  - [ ] Et : une invitation à co-écrire la Séquence Partagée est envoyée aux deux joueurs
  - [ ] Quand : je refuse
  - [ ] Alors : le demandeur est notifié et le PNJ reste disponible

### "Envoyer une demande d'Adopt sur un PNJ"

**En tant que** joueur qui a découvert un PNJ intéressant
**Je veux** envoyer une demande d'Adopt avec une proposition narrative
**Afin de** intégrer ce personnage dans ma propre histoire

- Critères d'acceptation :
  - [ ] Étant donné : je suis sur la fiche d'un PNJ disponible
  - [ ] Quand : je clique "Adopter" et je rédige ma proposition narrative
  - [ ] Alors : la demande est envoyée au créateur du PNJ (via ActivityPub si inter-instances)
  - [ ] Et : le PNJ passe en statut "En attente" et n'est plus disponible pour d'autres demandes simultanées

### "Co-écrire une Séquence Partagée"

**En tant que** joueur impliqué dans un lien accepté
**Je veux** co-écrire la scène narrative qui justifie le lien avec l'autre joueur
**Afin que** le lien entre nos personnages soit ancré dans une fiction partagée

- Critères d'acceptation :
  - [ ] Étant donné : une demande de lien a été acceptée
  - [ ] Alors : un espace d'écriture collaborative est ouvert pour les deux joueurs
  - [ ] Quand : la séquence est publiée
  - [ ] Alors : elle apparaît sur les fiches des deux personnages et sur les deux parties concernées

---

## Domaine 7 — Social & Fédération

### "Suivre une partie ou un joueur"

**En tant que** joueur solo
**Je veux** suivre la partie ou le profil d'un autre joueur (même sur une autre instance)
**Afin que** leurs nouveaux comptes-rendus apparaissent dans mon fil d'actualité

- Critères d'acceptation :
  - [ ] Étant donné : je suis sur le profil d'un joueur ou la page d'une partie
  - [ ] Quand : je clique "Suivre"
  - [ ] Alors : leurs publications apparaissent dans mon fil d'actualité chronologique
  - [ ] Et : cela fonctionne même si le joueur est sur une instance différente

### "Voir mon fil d'actualité"

**En tant que** joueur solo
**Je veux** voir un fil d'actualité chronologique de tous les comptes-rendus publiés par les joueurs et parties que je suis
**Afin de** rester connecté à la fiction partagée sans effort

- Critères d'acceptation :
  - [ ] Étant donné : je suis connecté
  - [ ] Alors : mon fil d'actualité affiche les comptes-rendus les plus récents des joueurs et parties suivis
  - [ ] Et : les nouveaux PNJ disponibles pour Adopt/Claim/Fork sont mis en évidence
  - [ ] Et : les Séquences Partagées impliquant des personnages que je suis apparaissent dans le fil

---

## Priorité d'implémentation

| Priorité | Domaine | Justification |
|----------|---------|---------------|
| 1 | Compte & Profil | Prérequis absolu |
| 2 | Parties | Contenant des comptes-rendus |
| 3 | Comptes-rendus | Valeur principale de l'outil |
| 4 | Personnages | Découle naturellement des comptes-rendus |
| 5 | Citations | Gain immédiat, haute valeur perçue |
| 6 | Liens | Le gameplay — arrive quand la base existe |
| 7 | Social & Fédération | Amplifie la valeur existante |
