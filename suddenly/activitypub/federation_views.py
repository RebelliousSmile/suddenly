"""
Federation search views — WebFinger lookup + remote profile (US-22).

DA-1: HTMX-first. These views serve HTML for federated discovery.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST

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
    is_suddenly = _is_suddenly_actor(ap_id)
    target_type = _resolve_remote_actor_type(ap_id, actor_data, is_suddenly=is_suddenly)

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

    # Profile enrichment (DEC-C5, Phase 4): parties/personnages/activité for a
    # Suddenly actor, résumé + activité récente only otherwise. Any fetch
    # failure inside must never surface as a 500 — degrade to empty sections.
    collections: dict[str, list[dict[str, Any]]] = {"activity": [], "games": [], "characters": []}
    try:
        from .follow_federation import fetch_remote_actor_collections

        collections = fetch_remote_actor_collections(actor_data, is_suddenly=is_suddenly)
    except Exception:
        logger.warning("Remote profile enrichment failed for %s", ap_id, exc_info=True)

    return htmx_render(
        request,
        full_template="federation/remote_profile.html",
        partial_template="federation/remote_profile.html",
        context={
            "actor": actor_data,
            "domain": domain,
            "ap_id": ap_id,
            "target_type": target_type,
            "is_following": is_following,
            "is_suddenly": is_suddenly,
            "activity": collections["activity"],
            "remote_games": collections["games"],
            "remote_characters": collections["characters"],
        },
    )


def _is_suddenly_actor(ap_id: str) -> bool:
    """True if the actor's home instance is a known Suddenly instance (NodeInfo-detected)."""
    from .models import FederatedServer

    domain = urlparse(ap_id).netloc
    server = FederatedServer.objects.filter(server_name=domain).first()
    return server is not None and server.is_suddenly_instance()


def _resolve_remote_actor_type(
    ap_id: str, actor_data: dict[str, Any], *, is_suddenly: bool | None = None
) -> str:
    """Classify a fetched remote actor as "user"/"character"/"game" (DEC-C4).

    Discriminator: AS2 ``type: "Group"`` -> Game; ``type: "Person"`` with a
    ``status`` key (unconditionally emitted by ``serialize_character``,
    namespaced ``suddenly:status`` in ``AP_CONTEXT``, never present on
    ``serialize_user``) -> Character. Both are additionally gated on the
    actor's home instance being a KNOWN Suddenly instance
    (``FederatedServer.is_suddenly_instance()``) — an actor from an unknown
    or explicitly non-Suddenly instance always resolves to "user"
    (Person-only), so a Mastodon actor never 500s even if its JSON happens to
    carry an unrelated "status" field. `is_suddenly` may be passed in by a
    caller that already computed it (`_is_suddenly_actor`), to avoid a
    duplicate `FederatedServer` lookup.
    """
    if is_suddenly is None:
        is_suddenly = _is_suddenly_actor(ap_id)

    if not is_suddenly:
        return "user"

    actor_kind = actor_data.get("type")
    if actor_kind == "Group":
        return "game"
    if actor_kind == "Person" and "status" in actor_data:
        return "character"
    return "user"


@require_POST
@login_required
def remote_follow_toggle(request: AuthenticatedRequest) -> HttpResponse:
    """Toggle follow on a remote ActivityPub actor. HTMX POST.

    Follow target is polymorphic (DEC-C4, Epic C #133): a remote actor is
    classified via ``_resolve_remote_actor_type`` before resolution, so
    following a remote Suddenly Character or Game actor creates a Follow
    against that target — not always a User. A non-Suddenly actor (Mastodon)
    always resolves to "user" and never 500s.
    """
    ap_id = request.POST.get("ap_id", "").strip()
    if not ap_id:
        return HttpResponseBadRequest("Missing ap_id")

    from django.conf import settings
    from django.shortcuts import render

    from suddenly.activitypub.inbox import (
        get_or_create_remote_character,
        get_or_create_remote_game,
    )
    from suddenly.activitypub.tasks import (
        get_or_create_remote_user,
        send_follow_activity,
        send_undo_follow_activity,
    )
    from suddenly.characters.models import Follow
    from suddenly.core.utils import content_type_for_actor

    actor_data = _fetch_actor(ap_id)
    if not actor_data:
        return HttpResponseBadRequest("Could not resolve remote actor")

    target_type = _resolve_remote_actor_type(ap_id, actor_data)

    if target_type == "character":
        remote_target = get_or_create_remote_character(ap_id)
    elif target_type == "game":
        remote_target = get_or_create_remote_game(ap_id)
    else:
        remote_target = get_or_create_remote_user(ap_id)

    if not remote_target:
        return HttpResponseBadRequest("Could not resolve remote actor")

    ct = content_type_for_actor(target_type)
    existing = Follow.objects.filter(
        follower=request.user,
        content_type=ct,
        object_id=remote_target.pk,
    ).first()

    if existing:
        send_undo_follow_activity.delay(str(request.user.pk), ap_id, target_type)
        is_following = False
    else:
        domain = settings.DOMAIN
        follow_ap_id = f"https://{domain}/users/{request.user.username}/follows/{remote_target.pk}"
        Follow.objects.create(
            follower=request.user,
            content_type=ct,
            object_id=remote_target.pk,
            remote=False,
            ap_id=follow_ap_id,
            accepted=False,
        )
        send_follow_activity.delay(str(request.user.pk), ap_id, follow_ap_id, target_type)
        is_following = True

    return render(
        request,
        "components/remote_follow_button.html",
        {"ap_id": ap_id, "target_type": target_type, "is_following": is_following},
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
