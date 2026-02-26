"""
ActivityPub models.

FederatedServer tracks known remote instances for moderation and
federation metrics. No federation logic lives here — this is structure only.
"""

from django.db import models

from suddenly.core.models import BaseModel


class ServerStatus(models.TextChoices):
    """Reachability/trust status of a remote instance."""

    UNKNOWN = "UNKNOWN", "Inconnu"
    FEDERATED = "FEDERATED", "Fédéré"
    BLOCKED = "BLOCKED", "Bloqué"


class FederatedServer(BaseModel):
    """
    Known remote ActivityPub instance.

    Populated from NodeInfo discovery. Used for moderation (block/allow)
    and federation health monitoring.
    """

    server_name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Instance domain name (e.g. mastodon.social)",
    )
    application_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Software reported by NodeInfo (e.g. suddenly, mastodon)",
    )
    application_version = models.CharField(
        max_length=50,
        blank=True,
        help_text="Software version reported by NodeInfo",
    )
    status = models.CharField(
        max_length=20,
        choices=ServerStatus.choices,
        default=ServerStatus.UNKNOWN,
        db_index=True,
    )
    user_count = models.IntegerField(
        default=0,
        help_text="Total user count from last NodeInfo fetch",
    )
    last_checked = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last successful NodeInfo fetch",
    )

    class Meta:
        verbose_name = "Instance fédérée"
        verbose_name_plural = "Instances fédérées"
        indexes = [
            models.Index(fields=["server_name"], name="fedserver_name_idx"),
            models.Index(fields=["status"], name="fedserver_status_idx"),
            models.Index(fields=["application_type"], name="fedserver_type_idx"),
        ]

    def __str__(self) -> str:
        return self.server_name

    def is_suddenly_instance(self) -> bool:
        """Return True if the remote instance runs Suddenly software."""
        return self.application_type == "suddenly"
