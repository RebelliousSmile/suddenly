"""
Game and Report models for Suddenly.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from suddenly.core.models import BaseModel


class Game(BaseModel):
    """
    A Game is an ongoing fiction that receives reports over time.
    It's an ActivityPub actor that can be followed.
    """

    # Content
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    # Free-form label (no catalogue). The narrative meta-model lives on
    # Character (TraitSet/Trait/Action); systems that don't transpose fall back
    # to the character's external sheet_url.
    game_system = models.CharField(max_length=100, blank=True, help_text="Ex: Mist Engine, D&D 5e")

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


class ReportQuerySet(models.QuerySet["Report"]):
    """Querysets for Report. The liberation ("wall") filter lives here and
    nowhere else (SUD-V1): a report crosses the wall when ``released_at`` is set,
    and only a released + published + public report is a public story."""

    def released(self) -> "ReportQuerySet":
        """Reports that have crossed the temporal wall — the single released
        filter of the codebase. If liberation ever moves to the Game level, only
        this method changes."""
        return self.filter(
            released_at__isnull=False,
            status=ReportStatus.PUBLISHED,
            visibility=ReportVisibility.PUBLIC,
        )

    def feed_visible(self) -> "ReportQuerySet":
        """Published + public reports listable in a reading feed.

        The temporal wall is a *local* concept (liberation axis): a local report
        must have crossed it (``released_at`` set) to appear. A remote report is
        already gated by its origin instance before federation (federation axis),
        so it passes on ``status``/``visibility`` alone — the local ``released_at``
        is never populated on ingest and must not filter remote content out.
        """
        return self.filter(
            status=ReportStatus.PUBLISHED,
            visibility=ReportVisibility.PUBLIC,
        ).filter(Q(remote=True) | Q(released_at__isnull=False))


class ReportTemporalKind(models.TextChoices):
    """Chronological label of a scene relative to its ``temporal_anchor``.

    Orthogonal to the reading order (``previous_report``): a flashback/flashforward
    stays *in* the reading chain, it is only tagged as anterior/posterior in the
    fiction's internal chronology.
    """

    NORMAL = "normal", _("Normal")
    FLASHBACK = "flashback", _("Flashback")
    FLASHFORWARD = "flashforward", _("Flashforward")


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
    # The language belongs to the *scene*, not to individual posts: Rapports
    # inherit it. BCP-47 tag (no enum) so it lines up with ActivityPub's
    # ``contentMap``, which is indexed by language tag ('fr', 'fr-CA', …).
    language = models.CharField(
        max_length=16,
        default="fr",
        help_text="Langue de la scène, BCP-47 ('fr', 'fr-CA'). Les Rapports en héritent.",
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
    released_at = models.DateTimeField(blank=True, null=True, db_index=True)
    session_date = models.DateField(null=True, blank=True)

    objects = ReportQuerySet.as_manager()

    # Tags (hashtags for discovery)
    tags = models.ManyToManyField("core.Tag", blank=True, related_name="reports")

    # ActivityPub
    remote = models.BooleanField(default=False)
    ap_id = models.URLField(blank=True, null=True, unique=True)

    # --- Fiction order (reading axis) ---------------------------------------
    # Explicit fiction order, distinct from published_at/created_at/session_date.
    # Source of truth: the self-FK ``previous_report``. Its reverse
    # ``next_reports`` yields continuations → free branching (tree/forest). No
    # business logic lives here — the invariants, reading and mutation live in
    # ``games/services.py`` (fiction_thread / set_previous / validate_fiction_links).
    # A hard FK never crosses federation: the remote link travels as a soft IRI
    # (``previous_report_iri``), and the CheckConstraint below forbids both at once.
    previous_report = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="next_reports",
    )
    previous_report_iri = models.URLField(max_length=500, null=True, blank=True)
    branch_order = models.PositiveIntegerField(default=0)

    # --- Chronology (temporal axis) -----------------------------------------
    # A flashback/flashforward stays in the reading chain; these fields only tag
    # its position in the fiction's internal chronology relative to an anchor.
    temporal_kind = models.CharField(
        max_length=20,
        choices=ReportTemporalKind.choices,
        default=ReportTemporalKind.NORMAL,
    )
    temporal_anchor = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="temporal_referrers",
    )
    temporal_anchor_iri = models.URLField(max_length=500, null=True, blank=True)
    temporal_label = models.CharField(max_length=120, blank=True)

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
        constraints = [
            # XOR local/remote: a fiction link is either a hard FK (local) or a
            # soft IRI (remote), never both. When ingestion resolves an IRI to a
            # known Report it MUST clear the IRI (the FK is the link).
            # `check=` (Django 5.0) vs `condition=` (5.1): django-stubs versions disagree,
            # so suppress call-arg and self-suppress when the ignore is unused (cross-version).
            models.CheckConstraint(  # type: ignore[call-arg, unused-ignore]
                name="report_previous_local_xor_remote",
                check=~models.Q(previous_report__isnull=False, previous_report_iri__gt=""),
            ),
            models.CheckConstraint(  # type: ignore[call-arg, unused-ignore]
                name="report_anchor_local_xor_remote",
                check=~models.Q(temporal_anchor__isnull=False, temporal_anchor_iri__gt=""),
            ),
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


class Like(BaseModel):
    """A user's like on a published scene (Report). #138.

    Persistence only — no denormalized counter at MVP: the button shows a heart,
    no number. The ``liked`` state is read on the feed via an ``Exists``
    annotation (never a per-card query), and a ``Count`` stays addable later
    without a migration. Uniqueness ``(user, report)`` makes the toggle
    idempotent; the DB constraint is the safety net against a fast double-click
    racing two concurrent creates.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="likes"
    )
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="likes")

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "report"], name="unique_user_report_like"),
        ]
        indexes = [
            models.Index(fields=["report"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} ♥ {self.report}"


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


class GameCast(BaseModel):
    """Declares that a character is *available* in a game.

    Distinct from :class:`~suddenly.characters.models.CharacterAppearance`
    (a posteriori, tied to a Report). ``Character.origin_game`` only says where
    a character was *born*; ``GameCast`` says where they may be summoned. It
    feeds the composer's actor selectors **before** the first post, breaking the
    circle "to post with an NPC it must appear / to appear it must be posted".

    A character born in game A may join the cast of game B — **same UUID**, never
    duplicated. A recovered NPC keeps its origin name, on purpose.
    """

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="cast")
    character = models.ForeignKey(
        "characters.Character", on_delete=models.CASCADE, related_name="castings"
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["game", "character"], name="unique_game_cast"),
        ]
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["game"]),
        ]

    def __str__(self) -> str:
        return f"{self.character.name} in {self.game.title} cast"


class RapportKind(models.TextChoices):
    DESCRIPTION = "description", _("Description")
    ACTION = "action", _("Action")
    DISCUSSION = "discussion", _("Discussion")
    NARRATION = "narration", _("Narration")
    # The scene's compte rendu, written when the scene is closed. Full Rapport;
    # its content crosses the wall to the Hub. Not an actor's line → no actor.
    CLOSURE = "closure", _("Closure")


class RapportStatus(models.TextChoices):
    """Publication status of a single Rapport (post), orthogonal to Report.status.

    A Rapport can be kept as a private draft ("Enregistrer en brouillon") inside
    a scene that is itself already published: the published thread ("fil") only
    renders ``published`` rapports, while ``draft`` ones stay invisible until
    their author decides to expose them.
    """

    DRAFT = "draft", _("Draft")
    PUBLISHED = "published", _("Published")


class Rapport(BaseModel):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="rapports")
    kind = models.CharField(max_length=20, choices=RapportKind.choices)
    content = models.TextField()
    status = models.CharField(
        max_length=20, choices=RapportStatus.choices, default=RapportStatus.DRAFT
    )
    actor = models.ForeignKey(
        "characters.Character",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="rapport_appearances",
    )
    # Explicit sequence position within the scene. New posts append (0 keeps the
    # created_at order); the scene-edit reorder arrows renumber to 0..n.
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "created_at"]
        indexes = [
            models.Index(fields=["report", "kind"]),
            models.Index(fields=["report", "status"]),
            models.Index(fields=["report", "order"]),
        ]

    def clean(self) -> None:
        # The actor carries the posture (composer rule 2c):
        #   narration   → never an actor (it *is* the GM's voice)
        #   description → optional (empty = "Voix du MJ", or a character)
        #   action      → required (someone acts)
        #   discussion  → required (a spoken line is embodied)
        #   closure     → never an actor (the scene's compte rendu, GM voice)
        if self.kind in (RapportKind.NARRATION, RapportKind.CLOSURE) and self.actor is not None:
            raise ValidationError({"actor": "This kind is the narrative voice; it takes no actor."})
        if self.kind in (RapportKind.ACTION, RapportKind.DISCUSSION) and self.actor is None:
            raise ValidationError({"actor": f"An actor is required for a {self.kind}."})

    def __str__(self) -> str:
        return f"{self.get_kind_display()} — {self.report}"


class RapportMedia(BaseModel):
    """One image, one description. Never several — a medium *is* a mood.

    The cardinality *is* the semantics: a ``OneToOneField`` (not a ForeignKey)
    makes it **impossible** to attach two images to the same description. Media
    only exists on a ``description`` rapport — enforced in :meth:`clean` (and the
    view layer); the one-media rule is enforced at the database by the OneToOne.
    """

    rapport = models.OneToOneField(Rapport, on_delete=models.CASCADE, related_name="media")
    image = models.ImageField(upload_to="rapports/%Y/%m/")
    alt = models.CharField(
        max_length=280,
        blank=True,
        help_text="Ce que montre l'image (a11y + ActivityPub Document.name).",
    )
    tone = models.CharField(
        max_length=80,
        blank=True,
        help_text="L'ambiance de l'image : lourde, feutrée…",
    )

    class Meta:
        ordering = ["created_at"]

    def clean(self) -> None:
        # Media only attaches to a description rapport (composer rule 2e).
        if self.rapport_id is not None and self.rapport.kind != RapportKind.DESCRIPTION:
            raise ValidationError(
                {"rapport": "Media can only be attached to a description rapport."}
            )

    def __str__(self) -> str:
        return f"Media — {self.rapport}"


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
