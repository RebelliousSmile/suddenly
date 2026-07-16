"""
Models backing "Se connecter avec le Fediverse".

Two tables:

- ``FediverseApp`` — one OAuth *client* per remote instance. Mastodon-compatible
  servers register apps dynamically (``POST /api/v1/apps``); we cache the returned
  ``client_id`` / ``client_secret`` here so we register with a given instance only
  once, not on every login.
- ``FediverseAccount`` — links a remote fediverse identity (instance + remote id)
  to a local :class:`~suddenly.users.models.User`. A user may link several.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models


class FediverseApp(models.Model):
    """A cached OAuth client registered with a single remote instance."""

    # Normalized host, e.g. "mastodon.social" (no scheme, no trailing slash).
    instance = models.CharField(max_length=255, unique=True)
    # Server family, best-effort from NodeInfo. Only Mastodon-API-compatible
    # servers (mastodon, pleroma, akkoma, gotosocial, pixelfed, …) are supported.
    software = models.CharField(max_length=50, blank=True, default="")
    client_id = models.CharField(max_length=255)
    client_secret = models.CharField(max_length=255)
    # The redirect URI registered with the instance. Stored so the exact same
    # value is replayed at the authorize + token steps (Mastodon requires a match).
    redirect_uri = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Fediverse app"
        verbose_name_plural = "Fediverse apps"

    def __str__(self) -> str:
        return f"{self.software or 'app'}@{self.instance}"


class FediverseAccount(models.Model):
    """A remote fediverse identity linked to a local account."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fediverse_accounts",
    )
    instance = models.CharField(max_length=255, db_index=True)
    # Remote account id as returned by the instance (stable per instance).
    uid = models.CharField(max_length=255)
    # Full webfinger handle, e.g. "alice@mastodon.social".
    acct = models.CharField(max_length=512)
    url = models.URLField(blank=True, default="")
    extra_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Fediverse account"
        verbose_name_plural = "Fediverse accounts"
        # A remote identity (instance + remote id) maps to exactly one local user.
        constraints = [
            models.UniqueConstraint(
                fields=["instance", "uid"], name="unique_fediverse_identity"
            )
        ]

    def __str__(self) -> str:
        return f"@{self.acct}"
