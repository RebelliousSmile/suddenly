"""
Modèles abstraits de base et modèles core.

Tous les modèles de l'application héritent de BaseModel.
"""

import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


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
