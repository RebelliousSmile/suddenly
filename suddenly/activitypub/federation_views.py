"""
Federation search views — WebFinger lookup + remote profile (US-22).

DA-1: HTMX-first. These views serve HTML for federated discovery.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse

from suddenly.core.types import AuthenticatedRequest
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

    is_following = False
    if request.user.is_authenticated:
        from django.contrib.contenttypes.models import ContentType

        from suddenly.characters.models import Follow
        from suddenly.users.models import User as UserModel

        remote_user = UserModel.objects.filter(ap_id=ap_id, remote=True).first()
        if remote_user:
            ct = ContentType.objects.get_for_model(UserModel)
            is_following = Follow.objects.filter(
                follower=request.user,
                content_type=ct,
                object_id=remote_user.pk,
            ).exists()

    return htmx_render(
        request,
        full_template="federation/remote_profile.html",
        partial_template="federation/remote_profile.html",
        context={
            "actor": actor_data,
            "domain": domain,
            "ap_id": ap_id,
            "is_following": is_following,
        },
    )


@login_required
def remote_follow_toggle(request: AuthenticatedRequest) -> HttpResponse:
    """Toggle follow on a remote ActivityPub actor. HTMX POST."""
    if request.method != "POST":
        from django.http import HttpResponseNotAllowed

        return HttpResponseNotAllowed(["POST"])

    ap_id = request.POST.get("ap_id", "").strip()
    if not ap_id:
        from django.http import HttpResponseBadRequest

        return HttpResponseBadRequest("Missing ap_id")

    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.shortcuts import render

    from suddenly.activitypub.tasks import (
        get_or_create_remote_user,
        send_follow_activity,
        send_undo_follow_activity,
    )
    from suddenly.characters.models import Follow
    from suddenly.users.models import User as UserModel

    remote_user = get_or_create_remote_user(ap_id)
    if not remote_user:
        from django.http import HttpResponseBadRequest

        return HttpResponseBadRequest("Could not resolve remote actor")

    ct = ContentType.objects.get_for_model(UserModel)
    existing = Follow.objects.filter(
        follower=request.user,
        content_type=ct,
        object_id=remote_user.pk,
    ).first()

    if existing:
        send_undo_follow_activity.delay(str(request.user.pk), ap_id)
        is_following = False
    else:
        domain = settings.DOMAIN
        follow_ap_id = f"https://{domain}/users/{request.user.username}/follows/{remote_user.pk}"
        Follow.objects.create(
            follower=request.user,
            content_type=ct,
            object_id=remote_user.pk,
            remote=False,
            ap_id=follow_ap_id,
            accepted=False,
        )
        send_follow_activity.delay(str(request.user.pk), ap_id, follow_ap_id)
        is_following = True

    return render(
        request,
        "components/remote_follow_button.html",
        {"ap_id": ap_id, "is_following": is_following},
    )


# ─── Helpers ──────────────────────────────────────────────────


def _lookup_webfinger(address: str) -> list[dict[str, str]]:
    """Resolve user@instance via WebFinger."""
    from ._http import fetch_ap_json

    parts = address.split("@")
    if len(parts) != 2:
        return []

    username, domain = parts

    # SSRF-safe fetch: the domain is user-supplied, so the WebFinger request must
    # go through the same allow/deny + IP-pin guard as actor fetches — never a
    # raw httpx.Client.
    url = f"https://{domain}/.well-known/webfinger?resource=acct:{address}"
    data = fetch_ap_json(url, accept="application/jrd+json")
    if not data:
        return []

    for link in data.get("links", []):
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


def _fetch_actor(url: str) -> dict[str, Any] | None:
    """Fetch an ActivityPub actor JSON. Blocks private/loopback IPs (SSRF protection)."""
    from ._http import fetch_ap_actor

    return fetch_ap_actor(url)
