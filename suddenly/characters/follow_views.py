"""
Follow/unfollow views for HTMX (DA-1). US-12.

Replaces the DRF FollowViewSet.toggle for the front-end.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from suddenly.core.types import AuthenticatedRequest

from .models import Follow


@require_POST
@login_required
def follow_toggle(request: AuthenticatedRequest) -> HttpResponse:
    """Toggle follow on a user/game/character. HTMX POST."""
    target_type = request.POST.get("target_type", "")
    target_id = request.POST.get("target_id", "")

    if not target_type or not target_id:
        from django.http import HttpResponseBadRequest

        return HttpResponseBadRequest("Missing target_type or target_id")

    # Resolve target
    from suddenly.core.utils import actor_model_for

    try:
        model_cls = actor_model_for(target_type)
    except ValueError:
        from django.http import HttpResponseBadRequest

        return HttpResponseBadRequest("Invalid target_type")

    target = get_object_or_404(model_cls, pk=target_id)

    # Prevent self-follow
    if target_type == "user" and target.pk == request.user.pk:
        from django.http import HttpResponseBadRequest

        return HttpResponseBadRequest("Cannot follow yourself")

    ct = ContentType.objects.get_for_model(model_cls)

    # Toggle
    existing = Follow.objects.filter(
        follower=request.user, content_type=ct, object_id=target.pk
    ).first()

    if existing:
        # DEC-D5 (Epic D, #134): unfollow is locked between two co-members of an
        # active game (AUTO or MANUAL alike) — the recourse while locked is a
        # report (epic F, out of scope), not an unfollow. Reuses the same
        # `active_comembership_exists` pivot as the teardown (DEC-D4), so the
        # lock and the auto-follow lifecycle always agree on "active".
        if target_type == "user":
            from typing import cast

            from suddenly.games.cast_follow import active_comembership_exists
            from suddenly.users.models import User

            if active_comembership_exists(request.user, cast(User, target)):
                return render(
                    request,
                    "components/follow_button.html",
                    {
                        "target": target,
                        "target_type": target_type,
                        "is_following": True,
                        "locked": True,
                    },
                )
        existing.delete()
        is_following = False
    else:
        Follow.objects.create(follower=request.user, content_type=ct, object_id=target.pk)
        is_following = True

    return render(
        request,
        "components/follow_button.html",
        {"target": target, "target_type": target_type, "is_following": is_following},
    )
