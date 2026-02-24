"""
User models for Suddenly.
"""

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class User(AbstractUser):
    """
    Custom user model for Suddenly.
    
    Each user is also an ActivityPub actor that can:
    - Publish games and reports
    - Own characters (PJ)
    - Receive notifications
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Profile
    display_name = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    
    # ActivityPub
    remote = models.BooleanField(default=False, help_text="True if federated user")
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

    def __str__(self):
        return self.display_name or self.username

    @property
    def actor_url(self):
        """ActivityPub actor URL."""
        if self.remote:
            return self.ap_id
        return f"{settings.AP_BASE_URL}/users/{self.username}"

    @property
    def actor_inbox(self):
        """ActivityPub inbox URL."""
        if self.remote:
            return self.inbox_url
        return f"{self.actor_url}/inbox"

    @property
    def actor_outbox(self):
        """ActivityPub outbox URL."""
        if self.remote:
            return self.outbox_url
        return f"{self.actor_url}/outbox"

    def get_display_name(self):
        """Return display name or username."""
        return self.display_name or self.username
