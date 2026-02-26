# Suddenly — Modèles de Données

**Version** : 1.0.0
**ORM** : Django 5.x
**Database** : PostgreSQL 16+

---

## Vue d'Ensemble

```
┌─────────────────────────────────────────────────────────────────┐
│                        DOMAINE MÉTIER                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐         ┌──────────┐         ┌──────────┐        │
│  │   User   │────────▶│   Game   │────────▶│  Report  │        │
│  │ (Person) │  owns   │(Collection)│ contains│ (Article)│        │
│  └──────────┘         └──────────┘         └──────────┘        │
│       │                    │                    │               │
│       │ owns/creates       │ origin             │ mentions      │
│       ▼                    ▼                    ▼               │
│  ┌──────────┐         ┌──────────┐         ┌──────────┐        │
│  │Character │◀────────│Character │────────▶│  Quote   │        │
│  │ (Person) │  links  │Appearance│  has    │  (Note)  │        │
│  └──────────┘         └──────────┘         └──────────┘        │
│       │                                                         │
│       │ requests                                                │
│       ▼                                                         │
│  ┌──────────┐         ┌──────────┐         ┌──────────┐        │
│  │  Link    │────────▶│Character │────────▶│  Shared  │        │
│  │ Request  │ creates │   Link   │ requires│ Sequence │        │
│  └──────────┘         └──────────┘         └──────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Table des Matières

1. [Conventions](#conventions)
2. [Modèles Core](#modèles-core)
   - [User](#user)
   - [Game](#game)
   - [Report](#report)
   - [Character](#character)
3. [Modèles Relations](#modèles-relations)
   - [CharacterAppearance](#characterappearance)
   - [ReportCast](#reportcast)
   - [Quote](#quote)
4. [Modèles Liens](#modèles-liens)
   - [LinkRequest](#linkrequest)
   - [CharacterLink](#characterlink)
   - [SharedSequence](#sharedsequence)
5. [Modèles Fédération](#modèles-fédération)
   - [FederatedServer](#federatedserver)
   - [Follow](#follow)
6. [Index et Contraintes](#index-et-contraintes)
7. [Migrations](#migrations)

---

## Conventions

### Clés Primaires

Tous les modèles utilisent **UUID** comme clé primaire :

```python
import uuid
from django.db import models

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

### Champs ActivityPub

Les modèles fédérables héritent de `ActivityPubMixin` :

```python
class ActivityPubMixin(models.Model):
    """Mixin pour les entités fédérables."""
    ap_id = models.URLField(unique=True, null=True, blank=True)
    inbox = models.URLField(null=True, blank=True)
    outbox = models.URLField(null=True, blank=True)
    local = models.BooleanField(default=True)

    class Meta:
        abstract = True

    def get_ap_id(self) -> str:
        """Retourne l'identifiant ActivityPub."""
        if self.ap_id:
            return self.ap_id
        return f"https://{settings.DOMAIN}{self.get_absolute_url()}"
```

### Nommage

| Élément | Convention | Exemple |
|---------|------------|---------|
| Table | `app_model` (auto) | `users_user`, `characters_character` |
| FK | `{model}_id` | `owner_id`, `game_id` |
| M2M | Pluriel | `followers`, `appearances` |
| Enum | SCREAMING_SNAKE | `CharacterStatus.NPC` |

---

## Modèles Core

### User

**App** : `users`
**Table** : `users_user`
**Type AP** : `Person`

Le compte utilisateur/joueur.

```python
from django.contrib.auth.models import AbstractUser

class User(AbstractUser, ActivityPubMixin):
    """Joueur - acteur ActivityPub principal."""

    # Identité
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    # ActivityPub
    ap_id = models.URLField(unique=True, null=True, blank=True)
    inbox = models.URLField(null=True, blank=True)
    outbox = models.URLField(null=True, blank=True)
    followers_url = models.URLField(null=True, blank=True)
    shared_inbox = models.URLField(null=True, blank=True)
    local = models.BooleanField(default=True)

    # Clés cryptographiques (pour signatures HTTP)
    public_key = models.TextField(null=True, blank=True)
    private_key = models.TextField(null=True, blank=True)  # Chiffré

    # Fédération
    federated_server = models.ForeignKey(
        'federation.FederatedServer',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )

    # Préférences de langue
    preferred_languages = models.JSONField(
        default=list,
        help_text="Langues acceptées pour le feed (codes ISO 639-1: ['fr', 'en'])"
    )
    content_language = models.CharField(
        max_length=10,
        default='fr',
        help_text="Langue par défaut des publications"
    )
    show_unlabeled_content = models.BooleanField(
        default=True,
        help_text="Afficher les contenus sans langue définie"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users_user'
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['ap_id']),
            models.Index(fields=['local']),
        ]
```

**Relations** :
- `games` → Game (1:N, owner)
- `characters` → Character (1:N, owner)
- `created_characters` → Character (1:N, creator)
- `reports` → Report (1:N, author)
- `quotes` → Quote (1:N, author)

---

### Game

**App** : `games`
**Table** : `games_game`
**Type AP** : `Group` (Acteur)

Une partie/campagne. **Acteur ActivityPub** suivable qui publie les comptes-rendus.

```python
class Game(BaseModel, ActivityPubMixin):
    """Partie - acteur ActivityPub suivable."""

    # Identité
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    description = models.TextField(blank=True)
    game_system = models.CharField(max_length=100, blank=True)  # "City of Mist", etc.

    # Propriétaire
    owner = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='games'
    )

    # Visibilité
    is_public = models.BooleanField(default=True)

    # ActivityPub (Game est un acteur)
    ap_id = models.URLField(unique=True, null=True, blank=True)
    inbox = models.URLField(null=True, blank=True)
    outbox = models.URLField(null=True, blank=True)
    followers_url = models.URLField(null=True, blank=True)
    local = models.BooleanField(default=True)

    # Clés cryptographiques (pour signatures HTTP)
    public_key = models.TextField(null=True, blank=True)
    private_key = models.TextField(null=True, blank=True)  # Chiffré

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'games_game'
        unique_together = [['owner', 'slug']]
        indexes = [
            models.Index(fields=['owner', 'is_public']),
            models.Index(fields=['game_system']),
            models.Index(fields=['ap_id']),
            models.Index(fields=['local']),
        ]
```

**Relations** :
- `owner` → User (N:1)
- `reports` → Report (1:N)
- `characters` → Character (1:N, origin_game)
- `followers` → Follow (1:N, via polymorphique)

---

### Report

**App** : `games`
**Table** : `games_report`
**Type AP** : `Article`

Un compte-rendu de partie.

```python
class ReportStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Brouillon'
    PUBLISHED = 'PUBLISHED', 'Publié'


class Report(BaseModel, ActivityPubMixin):
    """Compte-rendu de partie."""

    # Contenu
    title = models.CharField(max_length=255, blank=True)
    slug = models.SlugField(max_length=255)
    content = models.TextField()  # Markdown
    content_html = models.TextField(blank=True)  # Rendu HTML (cache)

    # Relations
    game = models.ForeignKey(
        'Game',
        on_delete=models.CASCADE,
        related_name='reports'
    )
    author = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='reports'
    )

    # Statut
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.DRAFT
    )
    published_at = models.DateTimeField(null=True, blank=True)

    # Langue du contenu (ISO 639-1)
    language = models.CharField(
        max_length=10,
        blank=True,
        help_text="Code langue ISO 639-1 (fr, en, de...)"
    )

    # ActivityPub
    ap_id = models.URLField(unique=True, null=True, blank=True)
    local = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'games_report'
        unique_together = [['game', 'slug']]
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['game', 'status']),
            models.Index(fields=['author']),
            models.Index(fields=['published_at']),
            models.Index(fields=['ap_id']),
            models.Index(fields=['language']),
        ]
```

**Relations** :
- `game` → Game (N:1)
- `author` → User (N:1)
- `appearances` → CharacterAppearance (1:N)
- `cast` → ReportCast (1:N, brouillon)
- `quotes` → Quote (1:N)

---

### Character

**App** : `characters`
**Table** : `characters_character`
**Type AP** : `Person`

Un personnage (PJ ou PNJ).

```python
class CharacterStatus(models.TextChoices):
    NPC = 'NPC', 'PNJ'
    PC = 'PC', 'PJ'
    CLAIMED = 'CLAIMED', 'Réclamé'
    ADOPTED = 'ADOPTED', 'Adopté'
    FORKED = 'FORKED', 'Dérivé'


class Character(BaseModel, ActivityPubMixin):
    """Personnage - acteur ActivityPub."""

    # Identité
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    description = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='characters/', null=True, blank=True)

    # Statut
    status = models.CharField(
        max_length=20,
        choices=CharacterStatus.choices,
        default=CharacterStatus.NPC
    )

    # Relations utilisateurs
    owner = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='characters'
    )
    creator = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='created_characters'
    )

    # Origine
    origin_game = models.ForeignKey(
        'games.Game',
        on_delete=models.CASCADE,
        related_name='characters'
    )

    # Lien parent (pour Fork)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='forks'
    )

    # Lien externe vers fiche technique
    sheet_url = models.URLField(blank=True)

    # ActivityPub
    ap_id = models.URLField(unique=True, null=True, blank=True)
    inbox = models.URLField(null=True, blank=True)
    outbox = models.URLField(null=True, blank=True)
    followers_url = models.URLField(null=True, blank=True)
    local = models.BooleanField(default=True)

    # Clés (pour signatures)
    public_key = models.TextField(null=True, blank=True)
    private_key = models.TextField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'characters_character'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['owner']),
            models.Index(fields=['creator']),
            models.Index(fields=['origin_game']),
            models.Index(fields=['ap_id']),
            models.Index(fields=['local', 'status']),
        ]
```

**Relations** :
- `owner` → User (N:1, nullable pour PNJ)
- `creator` → User (N:1)
- `origin_game` → Game (N:1)
- `parent` → Character (N:1, self, pour Fork)
- `forks` → Character (1:N, self)
- `appearances` → CharacterAppearance (1:N)
- `quotes` → Quote (1:N)
- `links_as_source` → CharacterLink (1:N)
- `links_as_target` → CharacterLink (1:N)

---

## Modèles Relations

### CharacterAppearance

**App** : `characters`
**Table** : `characters_characterappearance`

Lie un personnage à un compte-rendu (après publication).

```python
class AppearanceRole(models.TextChoices):
    MAIN = 'MAIN', 'Principal'
    SUPPORTING = 'SUPPORTING', 'Secondaire'
    MENTIONED = 'MENTIONED', 'Mentionné'


class CharacterAppearance(BaseModel):
    """Apparition d'un personnage dans un compte-rendu."""

    character = models.ForeignKey(
        'Character',
        on_delete=models.CASCADE,
        related_name='appearances'
    )
    report = models.ForeignKey(
        'games.Report',
        on_delete=models.CASCADE,
        related_name='appearances'
    )

    role = models.CharField(
        max_length=20,
        choices=AppearanceRole.choices,
        default=AppearanceRole.MENTIONED
    )
    context = models.TextField(blank=True)  # Description du rôle dans cette scène

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'characters_characterappearance'
        unique_together = [['character', 'report']]
        indexes = [
            models.Index(fields=['character']),
            models.Index(fields=['report']),
        ]
```

---

### ReportCast

**App** : `games`
**Table** : `games_reportcast`

Distribution prévue pour un brouillon (avant publication).

```python
class ReportCast(BaseModel):
    """Distribution prévue pour un compte-rendu (brouillon)."""

    report = models.ForeignKey(
        'Report',
        on_delete=models.CASCADE,
        related_name='cast'
    )

    # Soit personnage existant...
    character = models.ForeignKey(
        'characters.Character',
        on_delete=models.CASCADE,
        null=True, blank=True
    )

    # ...soit nouveau PNJ à créer
    new_character_name = models.CharField(max_length=255, blank=True)
    new_character_description = models.TextField(blank=True)

    role = models.CharField(
        max_length=20,
        choices=AppearanceRole.choices,
        default=AppearanceRole.MENTIONED
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'games_reportcast'
        indexes = [
            models.Index(fields=['report']),
        ]
```

---

### Quote

**App** : `quotes`
**Table** : `quotes_quote`
**Type AP** : `Note`

Citation mémorable d'un personnage.

```python
class QuoteVisibility(models.TextChoices):
    """Visibilité des citations.

    EPHEMERAL : Dialogues passe-partout, non fédérés, non persistants.
                Contenu temporaire visible uniquement en session (ex: "Bonjour").
                Non inclus dans la fédération ActivityPub.
    PRIVATE   : Persisté mais non fédéré. Visible uniquement par l'auteur.
    PUBLIC    : Persisté et fédéré via ActivityPub.
    """
    EPHEMERAL = 'EPHEMERAL', 'Éphémère (non fédéré, passe-partout)'
    PRIVATE = 'PRIVATE', 'Privée (non fédérée)'
    PUBLIC = 'PUBLIC', 'Publique (fédérée)'


class Quote(BaseModel, ActivityPubMixin):
    """Citation d'un personnage."""

    # Contenu
    content = models.TextField()  # La réplique
    context = models.TextField(blank=True)  # Situation

    # Relations
    character = models.ForeignKey(
        'characters.Character',
        on_delete=models.CASCADE,
        related_name='quotes'
    )
    author = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='quotes'
    )
    report = models.ForeignKey(
        'games.Report',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='quotes'
    )

    # Visibilité
    visibility = models.CharField(
        max_length=20,
        choices=QuoteVisibility.choices,
        default=QuoteVisibility.PUBLIC
    )

    # Langue du contenu (ISO 639-1)
    language = models.CharField(
        max_length=10,
        blank=True,
        help_text="Code langue ISO 639-1 (fr, en, de...)"
    )

    # ActivityPub
    ap_id = models.URLField(unique=True, null=True, blank=True)
    local = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'quotes_quote'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['character', 'visibility']),
            models.Index(fields=['author']),
            models.Index(fields=['ap_id']),
        ]
```

---

## Modèles Liens

### LinkRequest

**App** : `characters`
**Table** : `characters_linkrequest`
**Type AP** : `Offer`

Demande de Claim/Adopt/Fork.

```python
class LinkType(models.TextChoices):
    CLAIM = 'CLAIM', 'Claim'
    ADOPT = 'ADOPT', 'Adopt'
    FORK = 'FORK', 'Fork'


class LinkRequestStatus(models.TextChoices):
    PENDING = 'PENDING', 'En attente'
    ACCEPTED = 'ACCEPTED', 'Acceptée'
    REJECTED = 'REJECTED', 'Refusée'
    CANCELLED = 'CANCELLED', 'Annulée'


class LinkRequest(BaseModel):
    """Demande de lien entre personnages."""

    link_type = models.CharField(
        max_length=20,
        choices=LinkType.choices
    )

    # Demandeur
    requester = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='link_requests'
    )

    # PNJ cible
    target_character = models.ForeignKey(
        'Character',
        on_delete=models.CASCADE,
        related_name='link_requests_as_target'
    )

    # PJ proposé (pour Claim uniquement)
    proposed_character = models.ForeignKey(
        'Character',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='link_requests_as_proposed'
    )

    # Pour Fork : type de relation
    relationship = models.CharField(max_length=100, blank=True)

    # Messages
    message = models.TextField()  # Justification
    response_message = models.TextField(blank=True)  # Réponse

    # Statut
    status = models.CharField(
        max_length=20,
        choices=LinkRequestStatus.choices,
        default=LinkRequestStatus.PENDING
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    # ActivityPub (pour requêtes cross-instance)
    ap_id = models.URLField(unique=True, null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'characters_linkrequest'
        indexes = [
            models.Index(fields=['status', 'target_character']),
            models.Index(fields=['requester']),
            models.Index(fields=['link_type']),
        ]
```

---

### CharacterLink

**App** : `characters`
**Table** : `characters_characterlink`

Lien établi entre personnages (après acceptation).

```python
class CharacterLink(BaseModel):
    """Lien établi entre deux personnages."""

    link_type = models.CharField(
        max_length=20,
        choices=LinkType.choices
    )

    # PJ source
    source = models.ForeignKey(
        'Character',
        on_delete=models.CASCADE,
        related_name='links_as_source'
    )

    # PNJ/ancien personnage cible
    target = models.ForeignKey(
        'Character',
        on_delete=models.CASCADE,
        related_name='links_as_target'
    )

    # Requête d'origine
    link_request = models.OneToOneField(
        'LinkRequest',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )

    # Description du lien
    description = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'characters_characterlink'
        unique_together = [['source', 'target', 'link_type']]
        indexes = [
            models.Index(fields=['source']),
            models.Index(fields=['target']),
            models.Index(fields=['link_type']),
        ]
```

---

### SharedSequence

**App** : `characters`
**Table** : `characters_sharedsequence`

Séquence narrative partagée après acceptation d'un Claim/Adopt/Fork. **Requis pour MVP** : un lien sans proposition narrative est rejeté.

```python
class SharedSequence(BaseModel):
    """Séquence narrative partagée suite à un lien accepté.

    MVP : Obligatoire. Un Claim/Adopt/Fork sans SharedSequence est rejeté.
    Cette séquence décrit la scène narrative qui justifie le lien.
    """

    # Lien associé
    character_link = models.OneToOneField(
        'CharacterLink',
        on_delete=models.CASCADE,
        related_name='shared_sequence'
    )

    # Contenu narratif
    title = models.CharField(max_length=255)
    content = models.TextField()  # Markdown - la scène narrative
    content_html = models.TextField(blank=True)  # Rendu HTML (cache)

    # Auteurs (collaboration entre les deux joueurs)
    initiator = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='initiated_sequences',
        help_text="Le joueur qui a proposé le lien"
    )
    acceptor = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='accepted_sequences',
        help_text="Le joueur qui a accepté le lien"
    )

    # Parties concernées
    initiator_game = models.ForeignKey(
        'games.Game',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='shared_sequences_as_initiator'
    )
    acceptor_game = models.ForeignKey(
        'games.Game',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='shared_sequences_as_acceptor'
    )

    # Publication
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'characters_sharedsequence'
        indexes = [
            models.Index(fields=['character_link']),
            models.Index(fields=['initiator']),
            models.Index(fields=['acceptor']),
            models.Index(fields=['is_published', 'published_at']),
        ]
```

**Relations** :
- `character_link` → CharacterLink (1:1, obligatoire)
- `initiator` → User (N:1)
- `acceptor` → User (N:1)
- `initiator_game` → Game (N:1, nullable)
- `acceptor_game` → Game (N:1, nullable)

**Workflow** :
1. Bob propose un Claim avec `LinkRequest.message` (proposition narrative initiale)
2. Alice accepte → `CharacterLink` créé
3. Ensemble ils rédigent la `SharedSequence` (scène collaborative)
4. Publication → visible sur les deux parties

---

## Modèles Fédération

### FederatedServer

**App** : `federation`
**Table** : `federation_federatedserver`

Instance fédérée connue.

```python
class ServerStatus(models.TextChoices):
    UNKNOWN = 'UNKNOWN', 'Inconnu'
    FEDERATED = 'FEDERATED', 'Fédéré'
    BLOCKED = 'BLOCKED', 'Bloqué'


class FederatedServer(BaseModel):
    """Instance fédérée."""

    server_name = models.CharField(max_length=255, unique=True)  # domain

    # Info serveur (via NodeInfo)
    application_type = models.CharField(max_length=100, blank=True)  # suddenly, mastodon, etc.
    application_version = models.CharField(max_length=50, blank=True)

    # Statut
    status = models.CharField(
        max_length=20,
        choices=ServerStatus.choices,
        default=ServerStatus.UNKNOWN
    )

    # Stats
    user_count = models.IntegerField(default=0)
    last_checked = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'federation_federatedserver'
        indexes = [
            models.Index(fields=['server_name']),
            models.Index(fields=['status']),
            models.Index(fields=['application_type']),
        ]
```

---

### Follow

**App** : `federation`
**Table** : `federation_follow`

Abonnement (User suit User/Character/Game).

```python
class FollowTargetType(models.TextChoices):
    USER = 'USER', 'Utilisateur'
    CHARACTER = 'CHARACTER', 'Personnage'
    GAME = 'GAME', 'Partie'


class FollowStatus(models.TextChoices):
    PENDING = 'PENDING', 'En attente'
    ACCEPTED = 'ACCEPTED', 'Accepté'
    REJECTED = 'REJECTED', 'Refusé'


class Follow(BaseModel):
    """Abonnement."""

    follower = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='following_set'
    )

    # Cible polymorphique
    target_type = models.CharField(
        max_length=20,
        choices=FollowTargetType.choices
    )
    target_id = models.UUIDField()

    # Pour les follows distants
    target_ap_id = models.URLField(null=True, blank=True)

    # Statut
    status = models.CharField(
        max_length=20,
        choices=FollowStatus.choices,
        default=FollowStatus.PENDING
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'federation_follow'
        unique_together = [['follower', 'target_type', 'target_id']]
        indexes = [
            models.Index(fields=['follower']),
            models.Index(fields=['target_type', 'target_id']),
            models.Index(fields=['status']),
        ]
```

---

## Index et Contraintes

### Index Recommandés

```sql
-- Recherche PNJ disponibles
CREATE INDEX idx_character_status_local
ON characters_character(status, local)
WHERE status = 'NPC';

-- Comptes-rendus publiés par partie
CREATE INDEX idx_report_game_published
ON games_report(game_id, published_at DESC)
WHERE status = 'PUBLISHED';

-- Citations publiques par personnage
CREATE INDEX idx_quote_character_public
ON quotes_quote(character_id, created_at DESC)
WHERE visibility = 'PUBLIC';

-- Full-text search sur personnages
CREATE INDEX idx_character_fts
ON characters_character
USING gin(to_tsvector('french', name || ' ' || description));

-- Full-text search sur comptes-rendus
CREATE INDEX idx_report_fts
ON games_report
USING gin(to_tsvector('french', title || ' ' || content));
```

### Contraintes

```sql
-- Un PNJ ne peut pas avoir d'owner
ALTER TABLE characters_character
ADD CONSTRAINT check_npc_no_owner
CHECK (status != 'NPC' OR owner_id IS NULL);

-- Un Claim nécessite un proposed_character
ALTER TABLE characters_linkrequest
ADD CONSTRAINT check_claim_has_proposed
CHECK (link_type != 'CLAIM' OR proposed_character_id IS NOT NULL);

-- Un ReportCast doit avoir soit character soit new_character_name
ALTER TABLE games_reportcast
ADD CONSTRAINT check_cast_has_character
CHECK (character_id IS NOT NULL OR new_character_name != '');
```

---

## Migrations

### Ordre de Création

```bash
# 1. Apps de base
python manage.py makemigrations users
python manage.py makemigrations federation
python manage.py makemigrations games
python manage.py makemigrations characters
python manage.py makemigrations quotes

# 2. Appliquer
python manage.py migrate
```

### Données Initiales

```python
# users/fixtures/initial.json
# Créer un superuser initial si nécessaire

# federation/fixtures/initial.json
# Pas de données initiales requises
```
