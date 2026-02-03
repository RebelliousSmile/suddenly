"""
Game and Report models for Suddenly.
"""

import uuid

from django.db import models
from django.conf import settings


class Game(models.Model):
    """
    A Game is an ongoing fiction that receives reports over time.
    It's an ActivityPub actor that can be followed.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Content
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    game_system = models.CharField(max_length=100, blank=True, help_text="Ex: Mist Engine, D&D 5e")
    
    # Ownership
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="games"
    )
    
    # Visibility
    is_public = models.BooleanField(default=True)
    
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
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["owner", "is_public"]),
            models.Index(fields=["is_public", "updated_at"]),
        ]

    def __str__(self):
        return self.title

    @property
    def actor_url(self):
        """ActivityPub actor URL."""
        if self.remote:
            return self.ap_id
        return f"{settings.AP_BASE_URL}/games/{self.id}"


class ReportStatus(models.TextChoices):
    DRAFT = "draft", "Brouillon"
    PUBLISHED = "published", "Publié"


class Report(models.Model):
    """
    A Report is a narrative account added to a Game.
    Published reports become ActivityPub Notes.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Content
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField(help_text="Markdown with @character mentions")
    
    # Relations
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="reports")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.DRAFT
    )
    published_at = models.DateTimeField(blank=True, null=True)
    
    # ActivityPub
    remote = models.BooleanField(default=False)
    ap_id = models.URLField(blank=True, null=True, unique=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["game", "published_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return self.title or f"Report {self.id}"

    @property
    def is_published(self):
        return self.status == ReportStatus.PUBLISHED


class CastRole(models.TextChoices):
    """Role of a character in the cast."""
    MAIN = "main", "Principal"
    SUPPORTING = "supporting", "Secondaire"
    MENTIONED = "mentioned", "Mentionné"


class ReportCast(models.Model):
    """
    Characters planned for a report, defined before writing.
    
    This is the "distribution" (cast) workflow:
    1. Author creates a draft report
    2. Author defines which characters will appear via ReportCast
    3. Interface suggests @mentions during writing
    4. On publish, ReportCast entries become CharacterAppearance
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="cast"
    )
    
    # Either existing character OR new character to create
    character = models.ForeignKey(
        "characters.Character",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cast_entries",
        help_text="Existing character (null if creating new)"
    )
    
    # For creating new NPCs on the fly
    new_character_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Name for new NPC (if character is null)"
    )
    new_character_description = models.TextField(
        blank=True,
        help_text="Description for new NPC"
    )
    
    role = models.CharField(
        max_length=20,
        choices=CastRole.choices,
        default=CastRole.MENTIONED
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["role", "created_at"]
        indexes = [
            models.Index(fields=["report"]),
        ]

    def __str__(self):
        name = self.character.name if self.character else self.new_character_name
        return f"{name} in {self.report} cast"

    def is_new_character(self):
        """Returns True if this cast entry will create a new NPC."""
        return self.character is None and self.new_character_name
