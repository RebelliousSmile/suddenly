"""
Federation search views — WebFinger lookup + remote profile (US-22).

DA-1: HTMX-first. These views serve HTML for federated discovery.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from django.http import HttpRequest, HttpResponse

from suddenly.core.views import htmx_render

logger = logging.getLogger(__name__)


def federated_search(request: HttpRequest) -> HttpResponse:
    """Search for remote actors via WebFinger (US-22)."""
    query = request.GET.get("q", "").strip()
    results: list[dict[str, str]] = []
    error = ""

    if query:
        # Handle @user@instance or https://instance/users/user
        if query.startswith("http"):
            results = _lookup_by_url(query)
        elif "@" in query and not query.startswith("@"):
            results = _lookup_webfinger(query)
        elif query.startswith("@") and query.count("@") == 2:
            # @user@instance format
            results = _lookup_webfinger(query[1:])
        else:
            # Local search fallback — search local users
            results = _search_local(query)

        if not results and query:
            error = f"Aucun résultat pour « {query} »."

    return htmx_render(
        request,
        full_template="federation/search.html",
        partial_template="federation/_search_results.html",
        context={"query": query, "results": results, "error": error},
    )


def remote_profile(request: HttpRequest) -> HttpResponse:
    """Display a remote actor's profile (US-22)."""
    ap_id = request.GET.get("ap_id", "").strip()
    if not ap_id:
        from django.http import Http404

        raise Http404

    from suddenly.users.models import User

    # Check if already known locally
    user = User.objects.filter(ap_id=ap_id).first()
    if user:
        from django.shortcuts import redirect
        from django.urls import reverse

        return redirect(reverse("users:profile", kwargs={"username": user.username}))

    # Fetch remote actor
    actor_data = _fetch_actor(ap_id)
    if not actor_data:
        return htmx_render(
            request,
            full_template="federation/remote_profile.html",
            partial_template="federation/remote_profile.html",
            context={"error": "Impossible de charger ce profil distant."},
        )

    domain = urlparse(ap_id).hostname or ""

    return htmx_render(
        request,
        full_template="federation/remote_profile.html",
        partial_template="federation/remote_profile.html",
        context={
            "actor": actor_data,
            "domain": domain,
            "ap_id": ap_id,
        },
    )


# ─── Helpers ──────────────────────────────────────────────────


def _lookup_webfinger(address: str) -> list[dict[str, str]]:
    """Resolve user@instance via WebFinger."""
    import httpx

    parts = address.split("@")
    if len(parts) != 2:
        return []

    username, domain = parts

    try:
        url = f"https://{domain}/.well-known/webfinger?resource=acct:{address}"
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, headers={"Accept": "application/jrd+json"})

        if resp.status_code != 200:
            return []

        data = resp.json()
        links = data.get("links", [])

        for link in links:
            if link.get("rel") == "self" and "activity" in link.get("type", ""):
                actor_data = _fetch_actor(link["href"])
                if actor_data:
                    return [
                        {
                            "name": actor_data.get("name", username),
                            "username": f"@{username}@{domain}",
                            "ap_id": link["href"],
                            "domain": domain,
                            "summary": actor_data.get("summary", ""),
                            "type": actor_data.get("type", "Person"),
                        }
                    ]
    except Exception:
        logger.warning("WebFinger lookup failed for %s", address, exc_info=True)

    return []


def _lookup_by_url(url: str) -> list[dict[str, str]]:
    """Resolve an actor by direct URL."""
    actor_data = _fetch_actor(url)
    if not actor_data:
        return []

    domain = urlparse(url).hostname or ""
    username = actor_data.get("preferredUsername", "unknown")

    return [
        {
            "name": actor_data.get("name", username),
            "username": f"@{username}@{domain}",
            "ap_id": url,
            "domain": domain,
            "summary": actor_data.get("summary", ""),
            "type": actor_data.get("type", "Person"),
        }
    ]


def _search_local(query: str) -> list[dict[str, str]]:
    """Search local users by username."""
    from django.conf import settings

    from suddenly.users.models import User

    domain = getattr(settings, "DOMAIN", "localhost")
    users = User.objects.filter(is_active=True, remote=False, username__icontains=query)[:5]

    return [
        {
            "name": u.get_display_name(),
            "username": f"@{u.username}@{domain}",
            "ap_id": u.actor_url or "",
            "domain": domain,
            "summary": u.bio or "",
            "type": "Person",
        }
        for u in users
    ]


def _fetch_actor(url: str) -> dict | None:
    """Fetch an ActivityPub actor JSON. Blocks private/loopback IPs (SSRF protection)."""
    import socket

    import httpx

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return None

    # Block private/loopback IPs
    hostname = parsed.hostname
    if hostname:
        try:
            resolved = socket.getaddrinfo(hostname, None)
            for _, _, _, _, addr in resolved:
                ip = addr[0]
                import ipaddress

                ip_obj = ipaddress.ip_address(ip)
                if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
                    logger.warning("Blocked SSRF attempt to %s (%s)", url, ip)
                    return None
        except (socket.gaierror, ValueError):
            pass  # DNS resolution failed or invalid IP — let httpx handle it

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                url,
                headers={"Accept": "application/activity+json, application/ld+json"},
            )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        logger.warning("Failed to fetch actor %s", url, exc_info=True)

    return None
