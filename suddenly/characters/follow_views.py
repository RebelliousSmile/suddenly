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

    # Instance-wide ban (#136, DEC-F3) — blocked actors cannot follow or be followed
    from django.http import HttpResponseForbidden

    from suddenly.core.moderation import is_blocked

    if is_blocked(request.user) or (target_type == "user" and is_blocked(target)):
        return HttpResponseForbidden("Blocked users cannot follow")

    ct = ContentType.objects.get_for_model(model_cls)

    # Toggle
    existing = Follow.objects.filter(
        follower=request.user, content_type=ct, object_id=target.pk
    ).first()

    if existing:
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
