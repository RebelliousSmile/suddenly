"""
Mastodon-API OAuth client.

Implements the four HTTP calls of the "Sign in with Mastodon" flow against any
Mastodon-compatible instance (Mastodon, Pleroma, Akkoma, GoToSocial, Pixelfed):

1. ``POST /api/v1/apps``                    — register an OAuth client (once)
2. ``GET  /oauth/authorize``                — user consent (browser redirect)
3. ``POST /oauth/token``                    — exchange code for an access token
4. ``GET  /api/v1/accounts/verify_credentials`` — read the authenticated account

Every outbound request to a user-supplied instance goes through the project's
SSRF-safe pin helper (``_validate_and_pin``), never a raw client, so private /
loopback / link-local targets and DNS-rebinding are blocked — the same guarantee
the ActivitySub actor fetches rely on.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode

from django.conf import settings

from suddenly.activitypub._http import _validate_and_pin

logger = logging.getLogger(__name__)

# Minimal scope: we only need to read the account identity.
OAUTH_SCOPE = "read:accounts"


class FediverseClientError(Exception):
    """Raised when a call to a remote instance fails or is rejected."""


def _base_url(instance: str) -> str:
    # Always https: real instances 301-redirect http→https and we never follow
    # redirects. AP_ALLOW_INSECURE_HTTP only governs what _validate_and_pin
    # tolerates for inbound-supplied URLs — it must not downgrade our own calls.
    return f"https://{instance}"


def _post(
    url: str, data: dict[str, Any], *, headers: dict[str, str] | None = None
) -> dict[str, Any]:
    """SSRF-safe form POST returning parsed JSON, or raise FediverseClientError."""
    import httpx

    pinned = _validate_and_pin(url)
    if pinned is None:
        raise FediverseClientError(f"Refused to connect to {url}")
    request_url, extra_headers, extensions = pinned
    req_headers = {"Accept": "application/json", **extra_headers, **(headers or {})}
    try:
        with httpx.Client(timeout=10, follow_redirects=False) as client:
            resp = client.post(request_url, data=data, headers=req_headers, extensions=extensions)
    except Exception as exc:  # noqa: BLE001 — surface as a domain error
        raise FediverseClientError(f"Request to {url} failed: {exc}") from exc
    if resp.status_code != 200:
        raise FediverseClientError(f"{url} returned HTTP {resp.status_code}")
    try:
        return resp.json()  # type: ignore[no-any-return]
    except ValueError as exc:
        raise FediverseClientError(f"{url} returned non-JSON body") from exc


def _get(url: str, *, headers: dict[str, str] | None = None) -> dict[str, Any]:
    """SSRF-safe GET returning parsed JSON, or raise FediverseClientError."""
    import httpx

    pinned = _validate_and_pin(url)
    if pinned is None:
        raise FediverseClientError(f"Refused to connect to {url}")
    request_url, extra_headers, extensions = pinned
    req_headers = {"Accept": "application/json", **extra_headers, **(headers or {})}
    try:
        with httpx.Client(timeout=10, follow_redirects=False) as client:
            resp = client.get(request_url, headers=req_headers, extensions=extensions)
    except Exception as exc:  # noqa: BLE001
        raise FediverseClientError(f"Request to {url} failed: {exc}") from exc
    if resp.status_code != 200:
        raise FediverseClientError(f"{url} returned HTTP {resp.status_code}")
    try:
        return resp.json()  # type: ignore[no-any-return]
    except ValueError as exc:
        raise FediverseClientError(f"{url} returned non-JSON body") from exc


def detect_software(instance: str) -> str:
    """Best-effort NodeInfo probe for the server family. Empty string if unknown."""
    try:
        index = _get(f"{_base_url(instance)}/.well-known/nodeinfo")
        links = index.get("links", []) if isinstance(index, dict) else []
        # Standard rel is "http://nodeinfo.diaspora.software/ns/schema/<version>".
        href = next(
            (
                link["href"]
                for link in links
                if str(link.get("rel", "")).startswith(
                    "http://nodeinfo.diaspora.software/ns/schema/"
                )
            ),
            None,
        )
        if not href:
            return ""
        nodeinfo = _get(href)
        return str(nodeinfo.get("software", {}).get("name", "")).lower()
    except FediverseClientError:
        return ""


def register_app(instance: str, redirect_uri: str) -> dict[str, str]:
    """Register an OAuth client with ``instance``; return client_id/secret."""
    data = {
        "client_name": getattr(settings, "FEDIVERSE_APP_NAME", None) or settings.SITE_NAME,
        "redirect_uris": redirect_uri,
        "scopes": OAUTH_SCOPE,
        "website": getattr(settings, "AP_BASE_URL", ""),
    }
    payload = _post(f"{_base_url(instance)}/api/v1/apps", data)
    client_id = payload.get("client_id")
    client_secret = payload.get("client_secret")
    if not client_id or not client_secret:
        raise FediverseClientError(f"{instance} did not return OAuth credentials")
    return {"client_id": str(client_id), "client_secret": str(client_secret)}


def build_authorize_url(instance: str, client_id: str, redirect_uri: str, state: str) -> str:
    """Build the browser redirect URL to the instance's consent screen."""
    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": OAUTH_SCOPE,
            "state": state,
        }
    )
    return f"{_base_url(instance)}/oauth/authorize?{query}"


def exchange_code(
    instance: str,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> str:
    """Exchange an authorization code for an access token."""
    payload = _post(
        f"{_base_url(instance)}/oauth/token",
        {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code": code,
            "scope": OAUTH_SCOPE,
        },
    )
    token = payload.get("access_token")
    if not token:
        raise FediverseClientError(f"{instance} did not return an access token")
    return str(token)


def verify_credentials(instance: str, access_token: str) -> dict[str, Any]:
    """Read the authenticated account from the instance."""
    return _get(
        f"{_base_url(instance)}/api/v1/accounts/verify_credentials",
        headers={"Authorization": f"Bearer {access_token}"},
    )
