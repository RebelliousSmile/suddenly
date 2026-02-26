"""
Character models for Suddenly.

Characters are the core of Suddenly - they can be NPCs that become PCs,
get claimed, adopted, or forked by other players.
"""

import uuid

from django.db import models
from django.conf import settings

from suddenly.games.models import Game, Report


class CharacterStatus(models.TextChoices):
    """Status of a character."""
    NPC = "npc", "PNJ"
    PC = "pc", "PJ"
    CLAIMED = "claimed", "Réclamé"
    ADOPTED = "adopted", "Adopté"
    FORKED = "forked", "Forké"


class Character(models.Model):
    """
    A Character can be a PC or NPC, and can evolve between states.
    Each character is an ActivityPub actor.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identity
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="characters/", blank=True, null=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=CharacterStatus.choices,
        default=CharacterStatus.NPC
    )
    
    # Ownership
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_characters",
        help_text="Current owner (null for unclaimed NPCs)"
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_characters",
        help_text="Who created/mentioned this character first"
    )
    
    # Origin
    origin_game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name="characters",
        help_text="Game where this character was first mentioned"
    )
    
    # Lineage (for forks)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="forks",
        help_text="Parent character if this is a fork"
    )
    
    # External character sheet
    sheet_url = models.URLField(blank=True, null=True, help_text="Link to external character sheet")
    
    # ActivityPub
    remote = models.BooleanField(default=False)
    ap_id = models.URLField(blank=True, null=True, unique=True)
    inbox_url = models.URLField(blank=True, null=True)
    outbox_url = models.URLField(blank=True, null=True)
    public_key = models.TextField(blank=True, help_text="PEM-encoded public key")
    private_key = models.TextField(blank=True, help_text="PEM-encoded private key (local only)")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["origin_game"]),
            models.Index(fields=["owner"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    @property
    def is_available(self):
        """Is this character available for claim/adopt/fork?"""
        return self.status == CharacterStatus.NPC

    @property
    def actor_url(self) -> str | None:
        """ActivityPub actor URL."""
        if self.remote:
            return self.ap_id
        return f"{settings.AP_BASE_URL}/characters/{self.id}"

    @property
    def local(self) -> bool:
        """True if this character belongs to the local instance."""
        return not self.remote


class QuoteVisibility(models.TextChoices):
    """Visibility levels for quotes."""
    EPHEMERAL = "ephemeral", "Éphémère"
    PRIVATE = "private", "Privée"
    PUBLIC = "public", "Publique"


class Quote(models.Model):
    """
    A memorable quote from a character, BookWyrm-style.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Content
    content = models.TextField(help_text="The quote itself")
    context = models.TextField(blank=True, help_text="Situation when this was said")
    
    # Relations
    character = models.ForeignKey(
        Character,
        on_delete=models.CASCADE,
        related_name="quotes"
    )
    report = models.ForeignKey(
        Report,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quotes",
        help_text="Source report if any"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_quotes",
        help_text="Who recorded this quote"
    )
    
    # Visibility
    visibility = models.CharField(
        max_length=20,
        choices=QuoteVisibility.choices,
        default=QuoteVisibility.PUBLIC
    )
    
    # Ephemeral quotes expiration
    expires_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When this quote should disappear (for EPHEMERAL visibility)"
    )
    
    # ActivityPub
    remote = models.BooleanField(default=False)
    ap_id = models.URLField(blank=True, null=True, unique=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["character", "visibility"]),
            models.Index(fields=["visibility", "expires_at"]),
        ]

    def __str__(self):
        return f'"{self.content[:50]}..." - {self.character.name}'

    @property
    def is_expired(self):
        """Check if ephemeral quote has expired."""
        from django.utils import timezone
        if self.visibility != QuoteVisibility.EPHEMERAL:
            return False
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at


class AppearanceRole(models.TextChoices):
    """Role of a character in a report."""
    MAIN = "main", "Principal"
    SUPPORTING = "supporting", "Secondaire"
    MENTIONED = "mentioned", "Mentionné"


class CharacterAppearance(models.Model):
    """
    Links a character to a report where they appear.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    character = models.ForeignKey(
        Character,
        on_delete=models.CASCADE,
        related_name="appearances"
    )
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="character_appearances"
    )
    
    role = models.CharField(
        max_length=20,
        choices=AppearanceRole.choices,
        default=AppearanceRole.MENTIONED
    )
    context = models.TextField(blank=True, help_text="Description of their role in this scene")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["character", "report"]
        ordering = ["role", "character__name"]
        indexes = [
            models.Index(fields=["character", "report"]),
        ]

    def __str__(self):
        return f"{self.character.name} in {self.report}"


class LinkType(models.TextChoices):
    """Types of links between characters."""
    CLAIM = "claim", "Claim (rétcon)"
    ADOPT = "adopt", "Adoption"
    FORK = "fork", "Fork (dérivation)"


class LinkRequestStatus(models.TextChoices):
    """Status of a link request."""
    PENDING = "pending", "En attente"
    ACCEPTED = "accepted", "Acceptée"
    REJECTED = "rejected", "Refusée"
    CANCELLED = "cancelled", "Annulée"


class LinkRequest(models.Model):
    """
    A request to claim, adopt, or fork a character.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Type
    type = models.CharField(max_length=20, choices=LinkType.choices)
    
    # Actors
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="link_requests_made"
    )
    target_character = models.ForeignKey(
        Character,
        on_delete=models.CASCADE,
        related_name="link_requests_received",
        help_text="The NPC being claimed/adopted/forked"
    )
    proposed_character = models.ForeignKey(
        Character,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="link_requests_proposed",
        help_text="For claims: the existing PC being proposed"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=LinkRequestStatus.choices,
        default=LinkRequestStatus.PENDING
    )
    
    # Messages
    message = models.TextField(help_text="Explanation of the request")
    response_message = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "target_character"]),
            models.Index(fields=["requester", "status"]),
        ]

    def __str__(self):
        return f"{self.get_type_display()}: {self.requester} → {self.target_character}"


class CharacterLink(models.Model):
    """
    An established link between characters after a request is accepted.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    type = models.CharField(max_length=20, choices=LinkType.choices)
    
    source = models.ForeignKey(
        Character,
        on_delete=models.CASCADE,
        related_name="links_as_source",
        help_text="The PC"
    )
    target = models.ForeignKey(
        Character,
        on_delete=models.CASCADE,
        related_name="links_as_target",
        help_text="The former NPC"
    )
    
    link_request = models.OneToOneField(
        LinkRequest,
        on_delete=models.SET_NULL,
        null=True,
        related_name="resulting_link"
    )
    
    description = models.TextField(blank=True, help_text="Nature of the link")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.source.name} ←{self.get_type_display()}→ {self.target.name}"


class SharedSequenceStatus(models.TextChoices):
    """Status of a shared sequence."""
    DRAFT = "draft", "Brouillon"
    PUBLISHED = "published", "Publié"


class SharedSequence(models.Model):
    """
    Co-created content when a link is established.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    link = models.OneToOneField(
        CharacterLink,
        on_delete=models.CASCADE,
        related_name="shared_sequence"
    )
    
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField(help_text="Markdown content")
    
    status = models.CharField(
        max_length=20,
        choices=SharedSequenceStatus.choices,
        default=SharedSequenceStatus.DRAFT
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title or f"Sequence for {self.link}"


class Follow(models.Model):
    """
    A follow relationship (local or federated).
    
    Uses Django's ContentType framework for polymorphic targets
    (User, Character, or Game).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="following"
    )
    
    # Generic foreign key to support following Users, Characters, or Games
    from django.contrib.contenttypes.fields import GenericForeignKey
    from django.contrib.contenttypes.models import ContentType
    
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={
            'model__in': ('user', 'character', 'game')
        }
    )
    object_id = models.UUIDField()
    target = GenericForeignKey('content_type', 'object_id')
    
    # ActivityPub
    remote = models.BooleanField(default=False)
    ap_id = models.URLField(blank=True, null=True, unique=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["follower", "content_type", "object_id"]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["follower"]),
        ]

    def __str__(self):
        return f"{self.follower} follows {self.target}"
