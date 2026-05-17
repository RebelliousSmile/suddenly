"""
Modèles abstraits de base et modèles core.

Tous les modèles de l'application héritent de BaseModel.
"""

import uuid
from typing import Any

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.utils import OperationalError, ProgrammingError


class BaseModel(models.Model):
    """
    Modèle de base avec UUID et timestamps.

    Attributes:
        id: UUID comme clé primaire
        created_at: Date de création (auto)
        updated_at: Date de modification (auto)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.id}>"


class NotificationType(models.TextChoices):
    """All notification types (US-20, wireframe 11-notifications)."""

    LINK_REQUEST = "link_request", "Demande de lien"
    LINK_ACCEPTED = "link_accepted", "Demande acceptée"
    LINK_REJECTED = "link_rejected", "Demande refusée"
    NEW_REPORT = "new_report", "Nouveau compte-rendu"
    RECOMMENDATION = "recommendation", "Recommandation"
    MENTION = "mention", "Mention"
    INVITATION = "invitation", "Invitation"
    NEW_FOLLOWER = "new_follower", "Nouveau follower"
    SHARED_SEQUENCE = "shared_sequence", "Séquence Partagée"
    REVOCATION = "revocation", "Lien révoqué"


class Notification(BaseModel):
    """
    In-app notification for a user (US-20).

    Uses GenericForeignKey to point to the relevant object
    (LinkRequest, Report, Character, User, SharedSequence).
    """

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    type = models.CharField(max_length=30, choices=NotificationType.choices)

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="+",
    )

    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    target_object_id = models.UUIDField(null=True, blank=True)
    target = GenericForeignKey("target_content_type", "target_object_id")

    message = models.TextField(help_text="Human-readable notification text")
    is_read = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "-created_at"]),
            models.Index(fields=["recipient", "type"]),
        ]

    def __str__(self) -> str:
        return f"{self.type}: {self.message[:50]}"


class Tag(BaseModel):
    """Hashtag for cross-instance content discovery."""

    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"#{self.name}"


class NotificationPreference(BaseModel):
    """Per-user notification preferences (US-21)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    email_link_request = models.BooleanField(default=True)
    email_link_response = models.BooleanField(default=True)
    email_shared_sequence = models.BooleanField(default=True)
    email_new_report = models.BooleanField(default=False)
    email_recommendation = models.BooleanField(default=False)
    email_mention = models.BooleanField(default=True)
    email_invitation = models.BooleanField(default=True)
    email_new_follower = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"Notification prefs for {self.user}"


class ReportCategory(models.TextChoices):
    """Categories for content reports (US-27)."""

    SPAM = "spam", "Spam"
    HARASSMENT = "harassment", "Harcèlement"
    INAPPROPRIATE = "inappropriate", "Contenu inapproprié"
    OTHER = "other", "Autre"


class ContentReport(BaseModel):
    """Content report / signalement (US-27)."""

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports_made",
    )
    target_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    target_object_id = models.UUIDField()
    target = GenericForeignKey("target_content_type", "target_object_id")
    category = models.CharField(max_length=20, choices=ReportCategory.choices)
    comment = models.TextField(blank=True)
    resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.category}: {self.reporter}"


class UserBlock(BaseModel):
    """User-level block (US-33)."""

    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocks_made",
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocked_by",
    )

    class Meta:
        unique_together = ["blocker", "blocked"]

    def __str__(self) -> str:
        return f"{self.blocker} blocks {self.blocked}"


class UserMute(BaseModel):
    """User-level mute (US-33)."""

    muter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mutes_made",
    )
    muted = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="muted_by",
    )

    class Meta:
        unique_together = ["muter", "muted"]

    def __str__(self) -> str:
        return f"{self.muter} mutes {self.muted}"


class DonationPrompt(BaseModel):
    """Tracks donation prompts sent to users based on usage.

    Every N posts (configurable), a usage report is generated with
    a donation suggestion. If the user donated this month, no prompt.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="donation_prompts",
    )
    posts_at_prompt = models.IntegerField(
        help_text="User's total post count when this prompt was generated",
    )
    donated = models.BooleanField(
        default=False,
        help_text="True if user donated in response to this prompt",
    )
    donated_at = models.DateTimeField(null=True, blank=True)
    amount_suggested = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Suggested donation amount based on usage",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Donation prompt for {self.user} at {self.posts_at_prompt} posts"


class UserUsageStats(BaseModel):
    """Cached usage stats for donation prompt calculation.

    Updated on each post. Used to determine when to show
    the next donation prompt.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="usage_stats",
    )
    total_posts = models.IntegerField(default=0)
    total_quotes = models.IntegerField(default=0)
    total_link_requests = models.IntegerField(default=0)
    posts_since_last_prompt = models.IntegerField(default=0)
    last_donation_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "User usage stats"
        verbose_name_plural = "User usage stats"

    def __str__(self) -> str:
        return f"Usage: {self.user} ({self.total_posts} posts)"

    @property
    def donated_this_month(self) -> bool:
        """True if user made a donation in the current calendar month."""
        if not self.last_donation_date:
            return False
        from django.utils import timezone

        now = timezone.now().date()
        return (
            self.last_donation_date.year == now.year
            and self.last_donation_date.month == now.month
        )

    def should_prompt(self, interval: int = 10) -> bool:
        """True if enough posts since last prompt and no donation this month."""
        if self.donated_this_month:
            return False
        return self.posts_since_last_prompt >= interval


class InstanceSettings(models.Model):
    """
    Singleton model for instance-wide configuration.

    Only one row ever exists (pk=1). Use `InstanceSettings.get()` to access it.
    Direct instantiation outside of `get()` is discouraged.
    """

    name = models.CharField(max_length=100, blank=False)
    description = models.TextField(blank=True)
    language = models.CharField(
        max_length=10,
        choices=settings.LANGUAGES,
        default="fr",
    )
    registrations_open = models.BooleanField(default=True)

    # Donation system
    donation_enabled = models.BooleanField(
        default=False,
        help_text="Enable donation prompts based on usage",
    )
    donation_url = models.URLField(
        blank=True,
        help_text="URL to donation page (Ko-fi, Liberapay, etc.)",
    )
    donation_prompt_interval = models.IntegerField(
        default=10,
        help_text="Show donation prompt every N posts",
    )

    class Meta:
        verbose_name = "Instance Settings"
        verbose_name_plural = "Instance Settings"

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        # Enforce singleton: pk is always 1.
        self.pk = 1
        # Invalidate the cache so the next call to get() re-fetches from DB.
        from django.core.cache import cache  # local import avoids any circular-import risk

        cache.delete("instance_settings")
        super().save(*args, **kwargs)

    @classmethod
    def get(cls) -> "InstanceSettings":
        """
        Return the singleton InstanceSettings, using a 5-minute cache.

        Falls back to a default unsaved instance when the DB is unavailable
        (e.g. during the very first `migrate` run before tables exist).
        """
        from django.core.cache import cache  # local import avoids any circular-import risk

        cached: InstanceSettings | None = cache.get("instance_settings")
        if cached is not None:
            return cached

        try:
            instance, _ = cls.objects.get_or_create(
                pk=1,
                defaults={
                    "name": getattr(settings, "SITE_NAME", "Suddenly"),
                    "description": getattr(settings, "SITE_DESCRIPTION", "") or "",
                    "language": getattr(settings, "LANGUAGE_CODE", "fr"),
                },
            )
            cache.set("instance_settings", instance, 300)
            return instance
        except (OperationalError, ProgrammingError):
            # DB not yet available (e.g. first boot before migrations).
            return cls(
                pk=1,
                name=getattr(settings, "SITE_NAME", "Suddenly"),
                description=getattr(settings, "SITE_DESCRIPTION", "") or "",
                language=getattr(settings, "LANGUAGE_CODE", "fr"),
            )
