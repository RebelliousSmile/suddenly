"""
Follow/unfollow views for HTMX (DA-1). US-12.

Replaces the DRF FollowViewSet.toggle for the front-end.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from .models import Character, Follow


@login_required
def follow_toggle(request: HttpRequest) -> HttpResponse:
    """Toggle follow on a user/game/character. HTMX POST."""
    if request.method != "POST":
        from django.http import HttpResponseNotAllowed

        return HttpResponseNotAllowed(["POST"])

    target_type = request.POST.get("target_type", "")
    target_id = request.POST.get("target_id", "")

    if not target_type or not target_id:
        from django.http import HttpResponseBadRequest

        return HttpResponseBadRequest("Missing target_type or target_id")

    # Resolve target
    from suddenly.games.models import Game
    from suddenly.users.models import User

    model_map = {"user": User, "game": Game, "character": Character}
    model_cls = model_map.get(target_type)
    if not model_cls:
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
