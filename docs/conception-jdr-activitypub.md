# Suddenly — Réseau fédéré de fiction partagée

**Site** : suddenly.social

## Pitch

Un réseau de comptes-rendus de parties où les PNJ des uns peuvent devenir les PJ des autres.

Les joueurs publient leurs comptes-rendus de partie. Les PNJ mentionnés deviennent des points d'ancrage que d'autres joueurs peuvent réclamer, adopter ou dériver pour tisser des liens entre fictions indépendantes.

Le nom "Suddenly" évoque ce moment où l'inattendu surgit — quand un personnage apparaît soudainement dans une autre histoire.

---

## Concepts clés

### Partie (Game)

Une fiction continue appartenant à un joueur. Peut recevoir plusieurs comptes-rendus au fil du temps. Contient un système de jeu et des personnages.

### Compte-rendu (Report)

Un récit ajouté à une partie. Pas de notion de "session" — le joueur publie quand il veut, à son rythme.

**Workflow de rédaction :**
1. Création du brouillon dans une partie
2. Définition de la "distribution" (cast) : les PJ et PNJ qui apparaîtront
3. Rédaction avec insertion de mentions `@personnage` proposées par l'interface
4. Publication → les personnages deviennent disponibles pour le réseau

### Personnage (PJ / PNJ)

Entité unifiée dont le statut peut évoluer. Un personnage est créé dans une partie d'origine mais peut intervenir dans n'importe quelle partie du réseau fédéré.

### Citation (Quote)

Réplique mémorable d'un personnage, à la manière des citations de livres dans BookWyrm. Trois niveaux de visibilité :
- **Éphémère** — disparaît après la session
- **Privée** — visible uniquement par le créateur
- **Publique** — visible par tous, peut être fédérée

### PNJ déclaré

Personnage non-joueur mentionné dans un compte-rendu. Fiche minimale : nom, description, contexte d'apparition. Peut être réclamé, adopté ou forké par d'autres joueurs.

---

## Types de liens

### 1. Claim (rétcon)

> "Ton PNJ c'était mon PJ depuis le début."

Le joueur propose que son PJ existant était en réalité le PNJ décrit. Si accepté :
- Le PNJ est remplacé par le PJ dans la fiction
- La scène originale est rejouée/réécrite ensemble
- Le PJ gagne cette scène dans son historique

**Contrainte** : nécessite une cohérence narrative (le PJ pouvait être là à ce moment).

### 2. Adopt (reprise)

> "Ton PNJ m'intéresse, j'en fais mon PJ à partir de maintenant."

Le joueur reprend le PNJ comme nouveau PJ. Si accepté :
- Le PNJ devient un PJ à date fixe
- L'historique du PNJ (apparitions précédentes) est conservé
- Le nouveau joueur en prend le contrôle narratif

**Contrainte** : le PNJ ne doit pas être déjà réclamé ou adopté.

### 3. Fork (dérivation)

> "Je crée un PJ inspiré de ton PNJ, mais distinct."

Le joueur crée un nouveau PJ lié au PNJ sans le remplacer. Si accepté :
- Un lien de parenté est établi (nièce, ancien associé, sosie...)
- Les deux personnages coexistent
- Pas de contrainte de cohérence stricte

**Usage** : quand le PNJ a trop de passif pour être repris tel quel.

---

## Séquence de jeu partagée

Quand un lien est accepté, une séquence de jeu est déclenchée pour sceller la connexion.

### Format (à définir)

Options possibles :
- Échange de posts narratifs asynchrones
- Scène écrite à quatre mains
- Mini-scénario avec résolution légère
- Simple validation narrative (chacun écrit sa version, on harmonise)

### Résultat

La séquence produit un contenu "canonique" partagé, visible dans l'historique des deux personnages et dans les comptes-rendus des deux joueurs.

---

## Acteurs ActivityPub

### Joueur (User)

- Inbox/outbox pour les notifications et interactions
- Publie des parties
- Gère ses PJ

### Partie (Game)

- Acteur suivable, regroupe une fiction continue
- Publie des comptes-rendus
- Liste ses personnages (PJ et PNJ)
- Les abonnés reçoivent les nouveaux comptes-rendus et citations

### PJ (personnage joueur)

- Acteur à part entière, suivable
- Historique des scènes jouées
- Liens vers PNJ réclamés/adoptés/forkés

### PNJ (personnage non-joueur)

- Créé automatiquement lors d'une partie
- Statut : disponible / réclamé / adopté / forké
- Peut être suivi (pour être notifié si quelqu'un le réclame)

### Quote (Citation)

- Réplique mémorable d'un personnage
- Peut être fédérée si publique
- Apparaît sur le profil du personnage et dans les fils d'actualité

---

## Activités fédérées

| Activité | Déclencheur | Effet |
|----------|-------------|-------|
| `Create(Game)` | Nouvelle partie publique | Visible par les abonnés du joueur |
| `Create(Note)` | Publication compte-rendu | Visible par les abonnés de la partie |
| `Create(Character)` | Déclaration PNJ | Le PNJ devient disponible |
| `Create(Quote)` | Nouvelle citation publique | Visible par les abonnés du personnage |
| `Delete(Quote)` | Suppression citation | Retirée du réseau |
| `Offer(Claim)` | Proposition de claim | Notification au créateur du PNJ |
| `Offer(Adopt)` | Proposition d'adoption | Notification au créateur du PNJ |
| `Offer(Fork)` | Proposition de fork | Notification au créateur du PNJ |
| `Accept(Offer)` | Acceptation d'un lien | Déclenche séquence de jeu |
| `Reject(Offer)` | Refus d'un lien | Fin de la proposition |
| `Update(Note)` | Réécriture compte-rendu | Après claim accepté |

---

## Stack technique

- **Framework** : Python / Django (inspiré BookWyrm)
- **Base de données** : PostgreSQL
- **ActivityPub** : implémentation custom ou extraction de BookWyrm
- **Frontend** : à définir (templates Django ou SPA séparée)

---

## Modèle de données

### User (Joueur)

Le compte utilisateur, distinct des personnages.

```
User
├── id: UUID (PK)
├── username: string (unique, identifiant ActivityPub)
├── email: string (unique)
├── display_name: string
├── bio: text (nullable)
├── avatar: url (nullable)
├── remote: boolean (false = local, true = fédéré)
├── inbox_url: url (nullable, pour ActivityPub)
├── outbox_url: url (nullable, pour ActivityPub)
├── created_at: datetime
└── updated_at: datetime
```

### Game (Partie)

Une fiction continue, alimentée par des comptes-rendus au fil du temps. Acteur ActivityPub suivable.

```
Game
├── id: UUID (PK)
├── title: string
├── description: text (nullable)
├── game_system: string (nullable)
├── owner_id: FK → User
├── is_public: boolean
├── remote: boolean
├── ap_id: url (nullable, identifiant ActivityPub)
├── inbox_url: url (nullable)
├── outbox_url: url (nullable)
├── created_at: datetime
└── updated_at: datetime
```

### Character (Personnage)

Un personnage, qu'il soit PJ ou PNJ. Le statut peut évoluer. Les personnages sont créés dans une partie mais peuvent intervenir dans n'importe quelle partie du réseau.

```
Character
├── id: UUID (PK)
├── name: string
├── description: text
├── avatar: url (nullable)
├── status: enum [NPC, PC, CLAIMED, ADOPTED, FORKED]
├── owner_id: FK → User (nullable pour PNJ non réclamés)
├── creator_id: FK → User (celui qui l'a créé/mentionné)
├── origin_game_id: FK → Game (partie d'origine)
├── parent_id: FK → Character (nullable, pour les forks)
├── sheet_url: url (nullable, lien vers fiche externe)
├── remote: boolean
├── ap_id: url (nullable, identifiant ActivityPub)
├── created_at: datetime
└── updated_at: datetime
```

### Quote (Dialogue/Citation)

Une réplique mémorable d'un personnage, à la manière des citations BookWyrm.

```
Quote
├── id: UUID (PK)
├── character_id: FK → Character
├── content: text (la réplique)
├── context: text (nullable, situation de la citation)
├── report_id: FK → Report (nullable, compte-rendu source)
├── visibility: enum [EPHEMERAL, PRIVATE, PUBLIC]
├── author_id: FK → User (qui a enregistré la citation)
├── created_at: datetime
└── updated_at: datetime
```

**Visibilités des citations :**
- **EPHEMERAL** — visible uniquement pendant la session, disparaît après
- **PRIVATE** — visible uniquement par le créateur et le propriétaire du personnage
- **PUBLIC** — visible par tous, peut être fédérée

### Report (Compte-rendu)

Un récit ajouté à une partie. Une partie peut avoir plusieurs comptes-rendus.

```
Report
├── id: UUID (PK)
├── title: string (nullable)
├── content: text (markdown avec liens @personnage)
├── game_id: FK → Game
├── author_id: FK → User
├── status: enum [DRAFT, PUBLISHED]
├── published_at: datetime (nullable)
├── remote: boolean
├── ap_id: url (nullable)
├── created_at: datetime
└── updated_at: datetime
```

**Workflow de rédaction :**
1. Le joueur crée un brouillon de compte-rendu
2. Il définit les personnages (PJ/PNJ) qui apparaîtront via `ReportCast`
3. L'interface propose des mentions `@nom` à insérer dans le texte
4. À la publication, les `CharacterAppearance` sont créées automatiquement

### ReportCast (Distribution)

Les personnages prévus pour un compte-rendu, définis avant la rédaction.

```
ReportCast
├── id: UUID (PK)
├── report_id: FK → Report
├── character_id: FK → Character (nullable si nouveau PNJ)
├── new_character_name: string (nullable, si création à la volée)
├── new_character_description: text (nullable)
├── role: enum [MAIN, SUPPORTING, MENTIONED]
├── created_at: datetime
└── updated_at: datetime
```

À la publication du report :
- Les `ReportCast` avec `character_id` null créent de nouveaux `Character` (PNJ)
- Tous les `ReportCast` deviennent des `CharacterAppearance`

### CharacterAppearance (Apparition)

Lie un personnage à un compte-rendu.

```
CharacterAppearance
├── id: UUID (PK)
├── character_id: FK → Character
├── report_id: FK → Report
├── role: enum [MAIN, SUPPORTING, MENTIONED]
├── context: text (nullable, description du rôle dans cette scène)
├── created_at: datetime
└── updated_at: datetime
```

### LinkRequest (Demande de lien)

Une proposition de Claim, Adopt ou Fork.

```
LinkRequest
├── id: UUID (PK)
├── type: enum [CLAIM, ADOPT, FORK]
├── requester_id: FK → User
├── target_character_id: FK → Character (le PNJ visé)
├── proposed_character_id: FK → Character (nullable, le PJ pour Claim)
├── status: enum [PENDING, ACCEPTED, REJECTED, CANCELLED]
├── message: text (explication de la proposition)
├── response_message: text (nullable)
├── created_at: datetime
├── resolved_at: datetime (nullable)
└── updated_at: datetime
```

### CharacterLink (Lien établi)

Relation entre personnages après acceptation.

```
CharacterLink
├── id: UUID (PK)
├── type: enum [CLAIM, ADOPT, FORK]
├── source_id: FK → Character (le PJ)
├── target_id: FK → Character (l'ancien PNJ)
├── link_request_id: FK → LinkRequest
├── description: text (nullable, nature du lien)
├── created_at: datetime
└── updated_at: datetime
```

### SharedSequence (Séquence partagée)

Contenu co-créé lors d'un lien accepté.

```
SharedSequence
├── id: UUID (PK)
├── link_id: FK → CharacterLink
├── title: string (nullable)
├── content: text (markdown)
├── status: enum [DRAFT, PUBLISHED]
├── created_at: datetime
└── updated_at: datetime
```

### Follow (Abonnement)

Pour suivre des utilisateurs, personnages ou parties.

```
Follow
├── id: UUID (PK)
├── follower_id: FK → User
├── target_type: enum [USER, CHARACTER, GAME]
├── target_id: UUID
├── created_at: datetime
└── updated_at: datetime
```

---

## Relations clés

```
User ──1:N──> Game (owner)
User ──1:N──> Character (owner)
User ──1:N──> Character (creator)
User ──1:N──> Report (author)
User ──1:N──> Quote (author)

Game ──1:N──> Report
Game ──1:N──> Character (origin)

Character ──1:N──> Character (parent → forks)
Character ──N:M──> Report (via CharacterAppearance)
Character ──N:M──> Character (via CharacterLink)
Character ──1:N──> Quote

Report ──1:N──> CharacterAppearance
Report ──1:N──> ReportCast (brouillon)
Report ──1:N──> Quote (source)

LinkRequest ──1:1──> CharacterLink (si accepté)
CharacterLink ──1:1──> SharedSequence
```

---

## Index recommandés

- `Character(status)` — pour lister les PNJ disponibles
- `Character(origin_game_id)` — personnages d'une partie
- `Report(game_id, published_at)` — comptes-rendus d'une partie
- `CharacterAppearance(character_id, report_id)` — unique
- `ReportCast(report_id)` — cast d'un brouillon
- `Quote(character_id, visibility)` — citations publiques d'un personnage
- `LinkRequest(status, target_character_id)` — demandes en attente
- `Follow(follower_id, target_type, target_id)` — unique

---

## Jalons

### v0.1 — Fondations

- [ ] Modèle utilisateur / authentification
- [ ] Création et publication de comptes-rendus
- [ ] Déclaration de PNJ dans un compte-rendu
- [ ] Affichage public des comptes-rendus

### v0.2 — Personnages

- [ ] Création de PJ avec fiche minimale
- [ ] Historique des scènes par PJ
- [ ] Listing des PNJ disponibles

### v0.3 — Liens

- [ ] Proposition de Claim / Adopt / Fork
- [ ] Workflow acceptation / refus
- [ ] Séquence de jeu minimale (échange de textes)

### v0.4 — Fédération

- [ ] Acteurs ActivityPub pour joueurs et personnages
- [ ] Fédération des comptes-rendus (lisibles depuis Mastodon)
- [ ] Propositions de liens cross-instance

### v0.5 — Expérience

- [ ] Notifications
- [ ] Recherche de PNJ par univers / tags
- [ ] Graphe des liens entre personnages

---

## Questions ouvertes

1. **Gestion des conflits** — Deux joueurs veulent claim le même PNJ ?
2. **Modération** — Comment gérer les propositions abusives ou incohérentes ?
3. **Séquence partagée** — Format exact ? Échange asynchrone ? Éditeur collaboratif ?
4. **Fiche technique** — Simple lien externe (v1) ou connecteurs intégrés (v2+) ?

---

## Notes

- Projet initié à partir de réflexions sur Brumisa3 (Mist Engine) et l'idée de relier les fictions entre elles via ActivityPub.
- Solo first : les joueurs solo documentent naturellement leurs parties, ils alimenteront le réseau.
- Agnostique système : la fiche technique est un lien externe, Suddenly gère la couche narrative et sociale.
- Le nom "Suddenly" évoque le moment inattendu où les histoires se croisent.
