"""
Business logic for fediverse login: instance parsing, app registration caching,
and mapping a verified remote account to a local user.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlparse

from suddenly.users.models import User

from . import client
from .models import FediverseAccount, FediverseApp

logger = logging.getLogger(__name__)

# Mastodon-API-compatible server families we accept. Empty NodeInfo is tolerated
# (some servers hide it); the flow then still only works if the OAuth endpoints
# behave like Mastodon's, which is the point of the family list.
SUPPORTED_SOFTWARE = {"mastodon", "pleroma", "akkoma", "gotosocial", "pixelfed", "hometown"}

_HOST_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$")


class InvalidInstanceError(Exception):
    """Raised when the handle/instance a user typed cannot be parsed."""


def normalize_instance(raw: str) -> str:
    """Extract a bare instance host from user input.

    Accepts ``mastodon.social``, ``https://mastodon.social/``,
    ``@alice@mastodon.social`` and ``alice@mastodon.social``. Returns the
    lower-cased host. Raises :class:`InvalidInstanceError` on anything unusable.
    """
    value = (raw or "").strip().lower()
    if not value:
        raise InvalidInstanceError("empty")

    # Full URL form.
    if "://" in value:
        host = urlparse(value).hostname or ""
    elif "@" in value:
        # "@user@host" or "user@host" — the instance is the last @-segment.
        host = value.rstrip("/").split("@")[-1]
    else:
        # Bare host, possibly with a path.
        host = value.split("/")[0]

    host = host.strip().strip(".")
    if not _HOST_RE.match(host):
        raise InvalidInstanceError(host)
    return host


def get_or_register_app(instance: str, redirect_uri: str) -> FediverseApp:
    """Return the cached OAuth client for ``instance``, registering it if needed."""
    try:
        app = FediverseApp.objects.get(instance=instance)
        if app.redirect_uri == redirect_uri:
            return app
        # Our callback URL changed since we registered — re-register cleanly.
        app.delete()
    except FediverseApp.DoesNotExist:
        pass

    software = client.detect_software(instance)
    if software and software not in SUPPORTED_SOFTWARE:
        raise client.FediverseClientError(
            f"{instance} runs '{software}', which does not support this login method."
        )
    creds = client.register_app(instance, redirect_uri)
    return FediverseApp.objects.create(
        instance=instance,
        software=software,
        client_id=creds["client_id"],
        client_secret=creds["client_secret"],
        redirect_uri=redirect_uri,
    )


def _handle(account: dict[str, Any], instance: str) -> str:
    """Build a full ``user@instance`` webfinger handle from an account payload."""
    acct = str(account.get("acct") or account.get("username") or "").strip()
    if "@" not in acct:
        acct = f"{acct}@{instance}"
    return acct


def _unique_username(preferred: str) -> str:
    """Derive a locally-unique username from a fediverse username."""
    base = re.sub(r"[^a-zA-Z0-9_]", "", preferred) or "fedi_user"
    base = base[:120]
    candidate = base
    suffix = 1
    while User.objects.filter(username__iexact=candidate).exists():
        suffix += 1
        candidate = f"{base}_{suffix}"
    return candidate


def link_existing_user(user: User, instance: str, account: dict[str, Any]) -> FediverseAccount:
    """Attach a verified remote identity to an already-authenticated user."""
    fa, _created = FediverseAccount.objects.update_or_create(
        instance=instance,
        uid=str(account["id"]),
        defaults={
            "user": user,
            "acct": _handle(account, instance),
            "url": str(account.get("url") or ""),
            "extra_data": account,
        },
    )
    return fa


def resolve_or_create_user(
    instance: str, account: dict[str, Any], *, registrations_open: bool
) -> tuple[User, bool]:
    """Map a verified remote account to a local user.

    Returns ``(user, created)``. If no link exists a fresh local account is
    provisioned — never matched by email, which would allow account takeover.
    Raises :class:`PermissionError` if provisioning is needed but registration
    is closed on this instance.
    """
    uid = str(account["id"])
    try:
        fa = FediverseAccount.objects.select_related("user").get(instance=instance, uid=uid)
        # Refresh cached identity metadata on each login.
        fa.acct = _handle(account, instance)
        fa.url = str(account.get("url") or "")
        fa.extra_data = account
        fa.save(update_fields=["acct", "url", "extra_data", "last_login_at"])
        return fa.user, False
    except FediverseAccount.DoesNotExist:
        pass

    if not registrations_open:
        raise PermissionError("registrations_closed")

    username = _unique_username(str(account.get("username") or ""))
    user = User(
        username=username,
        display_name=str(account.get("display_name") or "")[:100],
        email=None,
    )
    # No local password: this account authenticates through the fediverse only.
    # A password can still be set later via the reset-by-email flow if an email
    # is added, keeping recovery possible.
    user.set_unusable_password()
    user.save()

    FediverseAccount.objects.create(
        user=user,
        instance=instance,
        uid=uid,
        acct=_handle(account, instance),
        url=str(account.get("url") or ""),
        extra_data=account,
    )
    logger.info("Provisioned local user %s from @%s", username, _handle(account, instance))
    return user, True
