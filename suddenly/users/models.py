"""
User models for Suddenly.

Each user is also an ActivityPub actor (Person) that can publish games,
own characters, and federate with other instances.
"""

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.urls import reverse


class User(AbstractUser):
    """
    Custom user model for Suddenly.

    Each user is also an ActivityPub actor that can:
    - Publish games and reports
    - Own characters (PJ)
    - Receive notifications

    The `remote` field tracks whether the user comes from a remote instance.
    Note: will be renamed to `local` in a future refactor (technical debt).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Profile
    display_name = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)

    # Email override — unique per instance
    email = models.EmailField(unique=True, blank=True, default="")

    # Language preferences
    content_language = models.CharField(max_length=10, default="fr")
    preferred_languages = models.JSONField(default=list, blank=True)
    show_unlabeled_content = models.BooleanField(default=True)

    # ActivityPub
    remote = models.BooleanField(default=False, db_index=True, help_text="True if federated user")
    ap_id = models.URLField(blank=True, null=True, unique=True)  # unique already implies index
    inbox_url = models.URLField(blank=True, null=True)
    outbox_url = models.URLField(blank=True, null=True)
    public_key = models.TextField(blank=True, help_text="PEM-encoded public key")
    private_key = models.TextField(blank=True, help_text="PEM-encoded private key (local only)")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        # username, email, ap_id are unique → implicit indexes; remote has db_index=True

    def __str__(self) -> str:
        return self.display_name or self.username

    def get_absolute_url(self) -> str:
        """Return the canonical URL for this user's public profile."""
        return reverse("users:profile", kwargs={"username": self.username})

    def get_display_name(self) -> str:
        """Return display name or username as fallback."""
        return self.display_name or self.username

    @property
    def actor_url(self) -> str:
        """ActivityPub actor URL."""
        if self.remote:
            return self.ap_id or ""
        return f"{settings.AP_BASE_URL}/users/{self.username}"

    @property
    def actor_inbox(self) -> str:
        """ActivityPub inbox URL."""
        if self.remote:
            return self.inbox_url or ""
        return f"{self.actor_url}/inbox"

    @property
    def actor_outbox(self) -> str:
        """ActivityPub outbox URL."""
        if self.remote:
            return self.outbox_url or ""
        return f"{self.actor_url}/outbox"
