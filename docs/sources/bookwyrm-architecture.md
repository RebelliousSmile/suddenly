# BookWyrm - Architecture de Reference

## TL;DR (30 secondes)

**BookWyrm** : Reseau social federe pour le suivi de livres (alternative a Goodreads)
**Stack** : Django + PostgreSQL + Celery + Redis + ActivityPub
**Pertinence Suddenly** : Implementation ActivityPub de reference, modeles User/Federation, custom object types

---

## Vue d'Ensemble

BookWyrm est un reseau social decentralise pour les lecteurs, construit sur ActivityPub. Il permet de :
- Suivre ses lectures et ecrire des critiques
- Federer avec d'autres instances BookWyrm
- Interoperer avec Mastodon/Pleroma

**Repository** : https://github.com/bookwyrm-social/bookwyrm
**Documentation** : https://docs.joinbookwyrm.com/

---

## Stack Technique

| Composant | Technologie | Role |
|-----------|-------------|------|
| **Backend** | Django (Python) | Framework web principal |
| **Base de donnees** | PostgreSQL | Stockage relationnel |
| **Queue** | Celery | Taches asynchrones (federation) |
| **Cache/Broker** | Redis | Backend Celery + cache |
| **Frontend** | Django Templates + Bulma | SSR + CSS framework |
| **Serveur web** | Nginx + Gunicorn | Reverse proxy + WSGI |
| **Deploiement** | Docker + docker-compose | Containerisation |

---

## Structure du Projet

```
bookwyrm/
├── bookwyrm/           # Application Django principale
│   ├── models/         # Modeles de donnees
│   ├── activitypub/    # Implementation ActivityPub
│   ├── views/          # Vues Django
│   ├── templates/      # Templates HTML
│   └── connectors/     # Integrations externes (OpenLibrary, etc.)
├── celerywyrm/         # Configuration Celery
├── static/             # Assets frontend
├── locale/             # Traductions i18n
├── nginx/              # Config serveur web
└── exports/            # Fonctionnalite export
```

---

## Implementation ActivityPub

### Acteurs (Actors)

BookWyrm utilise le type `Person` standard ActivityPub pour les utilisateurs :

```python
# Champs cles du User model
class User(AbstractUser):
    # Identite
    username = UsernameField()
    localname = CharField(unique=True)  # Pour instances locales
    name = CharField()                   # Nom d'affichage

    # Federation
    remote_id = CharField(unique=True)   # URI ActivityPub
    inbox = CharField()                  # URL inbox
    outbox = CharField()                 # URL outbox
    shared_inbox = CharField()           # Inbox partage
    followers_url = CharField()          # Collection followers

    local = BooleanField()               # Local vs Remote
    federated_server = ForeignKey()      # Instance d'origine
```

### Types d'Objets Personnalises

BookWyrm etend ActivityPub avec des types specifiques aux livres :

| Type BookWyrm | Equivalent AP Standard | Usage |
|---------------|------------------------|-------|
| `Review` | `Article` | Critique notee d'un livre |
| `Comment` | `Note` | Commentaire sur un livre |
| `Quotation` | `Note` | Citation extraite d'un livre |
| `Shelf` | `OrderedCollection` | Liste de lecture |
| `List` | `OrderedCollection` | Collection collaborative |

**Conversion pour federation** :
- Vers Mastodon : `Review` → `Article`, `Comment`/`Quotation` → `Note`
- Les livres sont attaches comme liens + image de couverture

### Activites Supportees

```
Utilisateurs : Follow, Accept, Reject, Block, Update, Delete, Undo, Move
Statuts     : Create, Like, Announce, Delete, Undo
Collections : Add, Remove
```

### Serialisation

Deux methodes cles dans `ActivitypubMixin` :

```python
# Entrant : JSON ActivityPub → Modele Django
def to_model(self, data):
    # Parse JSON-LD, cree/met a jour l'objet Django
    pass

# Sortant : Modele Django → JSON ActivityPub
def serialize(self):
    # Genere JSON-LD avec contexte appropriate
    pass
```

Le parametre `activitypub_field` permet de mapper les noms de champs :
```python
name = CharField(activitypub_field="preferredUsername")
```

---

## Modele de Donnees Simplifie

```
User (AbstractUser)
├── local: bool
├── remote_id: url (ActivityPub ID)
├── inbox/outbox/shared_inbox: urls
├── followers: M2M → User (via UserFollows)
├── blocks: M2M → User (via UserBlocks)
└── federated_server: FK → FederatedServer

FederatedServer
├── server_name: string
├── application_type: string (bookwyrm, mastodon, etc.)
└── status: enum (federated, blocked)

Status (base)
├── user: FK → User
├── content: text
├── remote_id: url
├── privacy: enum (public, unlisted, followers, direct)
└── published_date: datetime

Review(Status)
├── book: FK → Book
├── rating: decimal (0-5)
└── name: string (titre)

Book
├── title: string
├── remote_id: url
├── authors: M2M → Author
└── cover: image

Shelf (OrderedCollection)
├── user: FK → User
├── name: string
├── identifier: enum (to-read, reading, read, stopped)
└── books: M2M → Book (via ShelfBook)
```

---

## Patterns Reutilisables pour Suddenly

### 1. Gestion Remote vs Local

```python
class FederatedMixin:
    local = BooleanField(default=True)
    remote_id = CharField(unique=True, null=True)

    def save(self):
        if self.local and not self.remote_id:
            self.remote_id = f"https://{DOMAIN}/{self.path}"
        super().save()
```

### 2. Inbox/Outbox Pattern

```python
# Chaque acteur a :
# - inbox : recoit les activites entrantes
# - outbox : publie les activites sortantes

def receive_activity(request, user_id):
    activity = json.loads(request.body)
    activity_type = activity.get('type')

    handlers = {
        'Follow': handle_follow,
        'Create': handle_create,
        'Accept': handle_accept,
        # ...
    }
    return handlers[activity_type](activity)
```

### 3. Taches Celery pour Federation

```python
@celery_app.task
def broadcast_activity(activity, recipients):
    """Envoie une activite a tous les destinataires."""
    for inbox_url in recipients:
        sign_and_send(activity, inbox_url)

# Usage
broadcast_activity.delay(
    activity=status.to_activity(),
    recipients=get_follower_inboxes(user)
)
```

### 4. Suppression Soft

```python
def delete_user(user):
    # Ne pas supprimer, desactiver
    user.is_active = False
    user.email = mangle_email(user.email)
    user.save()

    # Nettoyer les contenus
    user.statuses.update(deleted=True, content="")
```

---

## Lecons pour Suddenly

### A Reprendre

1. **Architecture federee** : Modele User avec champs ActivityPub bien definis
2. **Types personnalises** : Etendre ActivityPub avec types metier (Report, Character, Quote)
3. **Conversion federation** : Transformer types custom en Note/Article pour Mastodon
4. **Celery pour async** : Federation via taches asynchrones
5. **Soft delete** : Conserver les references, anonymiser les donnees

### A Adapter

| BookWyrm | Suddenly |
|----------|----------|
| Book, Author | Game, Character |
| Review, Comment | Report, Quote |
| Shelf (to-read, reading) | Game status, Character status |
| Follow User | Follow Game, Follow Character |

### Types ActivityPub Suddenly

```python
# Proposition basee sur BookWyrm
SUDDENLY_TYPES = {
    'Report': 'Article',      # Compte-rendu → Article
    'Quote': 'Note',          # Citation → Note
    'Character': 'Person',    # Personnage → Person (acteur)
    'Game': 'Collection',     # Partie → Collection
    'LinkRequest': 'Offer',   # Claim/Adopt/Fork → Offer
}
```

---

## Ressources

- **Code source** : https://github.com/bookwyrm-social/bookwyrm
- **Documentation** : https://docs.joinbookwyrm.com/
- **ActivityPub spec** : https://docs.joinbookwyrm.com/activitypub.html
- **Guide contribution** : https://docs.joinbookwyrm.com/contributing.html
