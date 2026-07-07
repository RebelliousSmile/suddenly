"""
Game and Report models for Suddenly.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from suddenly.core.models import BaseModel


class GameSystem(models.Model):
    """
    A game rule system from the FoundryVTT catalog (or manually added).
    Synced from the official Foundry package registry.
    """

    slug = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=200)
    git_url = models.URLField(blank=True)
    is_deprecated = models.BooleanField(default=False)
    synced_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Game(BaseModel):
    """
    A Game is an ongoing fiction that receives reports over time.
    It's an ActivityPub actor that can be followed.
    """

    # Content
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    game_system = models.CharField(max_length=100, blank=True, help_text="Ex: Mist Engine, D&D 5e")
    game_system_ref = models.ForeignKey(
        GameSystem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="games",
    )

    # Ownership
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="games"
    )

    # Visibility
    is_public = models.BooleanField(default=True)

    # Media
    cover = models.ImageField(upload_to="games/", blank=True, null=True)

    # Tags (hashtags for discovery)
    tags = models.ManyToManyField("core.Tag", blank=True, related_name="games")

    # ActivityPub
    remote = models.BooleanField(default=False)
    ap_id = models.URLField(blank=True, null=True, unique=True)
    inbox_url = models.URLField(blank=True, null=True)
    outbox_url = models.URLField(blank=True, null=True)
    public_key = models.TextField(blank=True, help_text="PEM-encoded public key")
    private_key = models.TextField(blank=True, help_text="PEM-encoded private key (local only)")

    # Timeline
    started_at = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["owner", "is_public"]),
            models.Index(fields=["is_public", "updated_at"]),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def actor_url(self) -> str | None:
        """ActivityPub actor URL."""
        if self.remote:
            return self.ap_id
        return f"{settings.AP_BASE_URL}/games/{self.id}"

    @property
    def local(self) -> bool:
        """True if this game belongs to the local instance."""
        return not self.remote


class ReportStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    PUBLISHED = "published", _("Published")


class ReportVisibility(models.TextChoices):
    """Fediverse-compatible visibility scopes (US-29)."""

    PUBLIC = "public", _("Public")
    UNLISTED = "unlisted", _("Unlisted")
    FOLLOWERS = "followers", _("Followers only")


class Report(BaseModel):
    """
    A Report is a narrative account added to a Game.
    Published reports become ActivityPub Articles.
    """

    # Content
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField(help_text="Markdown with @character mentions")
    content_warning = models.CharField(
        max_length=500,
        blank=True,
        help_text="Content warning displayed before the report (US-30)",
    )

    # Relations
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="reports")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports"
    )

    # Language
    language = models.CharField(
        max_length=10,
        choices=settings.LANGUAGES,
        default="fr",
    )

    # Status & visibility
    status = models.CharField(
        max_length=20, choices=ReportStatus.choices, default=ReportStatus.DRAFT
    )
    visibility = models.CharField(
        max_length=20,
        choices=ReportVisibility.choices,
        default=ReportVisibility.PUBLIC,
        help_text="Who can see this report (US-29)",
    )
    published_at = models.DateTimeField(blank=True, null=True)
    # Liberation axis (the "wall"), orthogonal to status/visibility (SUD-V1).
    # A report can be published (federable) without being released (wall still
    # closed): `released_at` dates the moment a scene crosses the wall, turning
    # a game in progress into a resolved account. Symmetric with published_at.
    released_at = models.DateTimeField(blank=True, null=True)
    session_date = models.DateField(null=True, blank=True)

    # Tags (hashtags for discovery)
    tags = models.ManyToManyField("core.Tag", blank=True, related_name="reports")

    # ActivityPub
    remote = models.BooleanField(default=False)
    ap_id = models.URLField(blank=True, null=True, unique=True)

    class Meta:
        ordering = [
            models.F("session_date").asc(nulls_last=True),
            models.F("published_at").desc(nulls_last=True),
            "-created_at",
        ]
        indexes = [
            models.Index(fields=["game", "published_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return self.title or f"Report {self.id}"

    @property
    def is_published(self) -> bool:
        return self.status == ReportStatus.PUBLISHED

    @property
    def is_released(self) -> bool:
        """True once the report has crossed the temporal wall (SUD-V1).

        Mirror of ``is_published`` on the liberation axis: a released report is
        a resolved account, readable by the public; an unreleased one is still
        a game in progress, hidden behind the wall.
        """
        return self.released_at is not None


class CastRole(models.TextChoices):
    """Role of a character in the cast."""

    MAIN = "main", _("Main")
    SUPPORTING = "supporting", _("Supporting")
    MENTIONED = "mentioned", _("Mentioned")


class ReportCast(BaseModel):
    """
    Characters planned for a report, defined before writing.

    This is the "distribution" (cast) workflow:
    1. Author creates a draft report
    2. Author defines which characters will appear via ReportCast
    3. Interface suggests @mentions during writing
    4. On publish, ReportCast entries become CharacterAppearance
    """

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="cast")

    # Either existing character OR new character to create
    character = models.ForeignKey(
        "characters.Character",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cast_entries",
        help_text="Existing character (null if creating new)",
    )

    # For creating new NPCs on the fly
    new_character_name = models.CharField(
        max_length=100, blank=True, help_text="Name for new NPC (if character is null)"
    )
    new_character_description = models.TextField(blank=True, help_text="Description for new NPC")

    role = models.CharField(max_length=20, choices=CastRole.choices, default=CastRole.MENTIONED)

    class Meta:
        ordering = ["role", "created_at"]
        indexes = [
            models.Index(fields=["report"]),
        ]

    def __str__(self) -> str:
        name = self.character.name if self.character else self.new_character_name
        return f"{name} in {self.report} cast"

    def is_new_character(self) -> bool:
        """Returns True if this cast entry will create a new NPC."""
        return self.character is None and bool(self.new_character_name)


class RapportKind(models.TextChoices):
    DESCRIPTION = "description", _("Description")
    ACTION = "action", _("Action")
    DISCUSSION = "discussion", _("Discussion")
    NARRATION = "narration", _("Narration")


class Rapport(BaseModel):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="rapports")
    kind = models.CharField(max_length=20, choices=RapportKind.choices)
    content = models.TextField()
    actor = models.ForeignKey(
        "characters.Character",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="rapport_appearances",
    )

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["report", "kind"]),
        ]

    def clean(self) -> None:
        if self.kind == RapportKind.DISCUSSION and self.actor is None:
            raise ValidationError({"actor": "Actor is required for discussion type."})
        if self.kind != RapportKind.DISCUSSION and self.actor is not None:
            raise ValidationError({"actor": "Actor must be empty for non-discussion types."})

    def __str__(self) -> str:
        return f"{self.get_kind_display()} — {self.report}"


class RapportLink(BaseModel):
    """
    A directional link from a Rapport to one of its parents.

    Each row stores exactly one parent reference: either a local FK to another
    Rapport, or a remote ActivityPub IRI (URL). Exactly one must be set —
    enforced in clean().
    """

    rapport = models.ForeignKey(
        Rapport,
        on_delete=models.CASCADE,
        related_name="parent_links",
    )
    parent_rapport = models.ForeignKey(
        Rapport,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_links",
    )
    parent_iri = models.URLField(
        null=True,
        blank=True,
        max_length=500,
    )

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["rapport", "parent_rapport"],
                condition=Q(parent_rapport__isnull=False),
                name="unique_local_parent",
            ),
            models.UniqueConstraint(
                fields=["rapport", "parent_iri"],
                condition=Q(parent_iri__isnull=False),
                name="unique_remote_parent",
            ),
        ]

    def clean(self) -> None:
        has_local = self.parent_rapport_id is not None
        has_remote = bool(self.parent_iri)
        if has_local and has_remote:
            raise ValidationError(
                "A RapportLink must have exactly one parent: "
                "either parent_rapport or parent_iri, not both."
            )
        if not has_local and not has_remote:
            raise ValidationError(
                "A RapportLink must have exactly one parent: either parent_rapport or parent_iri."
            )

    def __str__(self) -> str:
        return f"{self.rapport} → {self.parent_rapport or self.parent_iri}"


class MarkerKind(models.TextChoices):
    START = "start", _("Start")
    END = "end", _("End")
    CHARACTER_APPEARS = "character_appears", _("Character appears")
    CHARACTER_LEAVES = "character_leaves", _("Character leaves")
    ORACLE = "oracle", _("Oracle")


CHARACTER_MARKER_KINDS: frozenset[str] = frozenset(
    {MarkerKind.CHARACTER_APPEARS, MarkerKind.CHARACTER_LEAVES}
)


class RapportMarker(BaseModel):
    """
    A structural marker within a Rapport sequence.

    Marks events such as scene start/end, character entrances/exits, and oracle moments.
    Character-related marker kinds require a linked character.
    """

    rapport = models.ForeignKey(Rapport, on_delete=models.CASCADE, related_name="markers")
    kind = models.CharField(max_length=30, choices=MarkerKind.choices)
    character = models.ForeignKey(
        "characters.Character",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="rapport_markers",
    )

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["rapport", "kind"]),
        ]

    def clean(self) -> None:
        if self.kind in CHARACTER_MARKER_KINDS and self.character is None:
            raise ValidationError({"character": "Character is required for this marker type."})
        if self.kind not in CHARACTER_MARKER_KINDS and self.character is not None:
            raise ValidationError({"character": "Character must be empty for this marker type."})

    def __str__(self) -> str:
        return f"{self.get_kind_display()} — {self.rapport}"
