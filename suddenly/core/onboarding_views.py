"""
Onboarding views — 3-step flow after first signup (wireframe 16-misc.md).
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render

from suddenly.core.types import AuthenticatedRequest


@login_required
def onboarding_step1(request: AuthenticatedRequest) -> HttpResponse:
    """Step 1: Complete profile (display name, bio, avatar)."""
    if request.method == "POST":
        user = request.user
        user.display_name = request.POST.get("display_name", "").strip()
        user.bio = request.POST.get("bio", "").strip()
        user.save(update_fields=["display_name", "bio"])
        return redirect("feed:onboarding_step2")

    return render(request, "onboarding/step1.html")


@login_required
def onboarding_step2(request: AuthenticatedRequest) -> HttpResponse:
    """Step 2: Discover instance (follow suggestions + local timeline)."""
    from suddenly.games.models import Game, Report
    from suddenly.users.models import User

    users = (
        User.objects.filter(is_active=True, remote=False)
        .exclude(pk=request.user.pk)
        .order_by("-date_joined")[:6]
    )
    games = Game.objects.filter(is_public=True, remote=False).order_by("-updated_at")[:3]
    recent = (
        Report.objects.feed_visible()
        .filter(remote=False)
        .select_related("game", "author")
        .order_by("-published_at")[:3]
    )

    return render(
        request,
        "onboarding/step2.html",
        {"suggested_users": users, "suggested_games": games, "recent_reports": recent},
    )


@login_required
def onboarding_step3(request: AuthenticatedRequest) -> HttpResponse:
    """Step 3: Choose first action."""
    return render(request, "onboarding/step3.html")
