"""
Notification views (US-20, US-21, wireframe 11).
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

from suddenly.core.models import Notification
from suddenly.core.types import AuthenticatedRequest
from suddenly.core.views import htmx_render


@login_required
def notification_list(request: AuthenticatedRequest) -> HttpResponse:
    """Notification center — list all notifications for current user."""
    notifications = (
        Notification.objects.filter(recipient=request.user)
        .select_related("actor")
        .order_by("-created_at")[:50]
    )

    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

    return htmx_render(
        request,
        full_template="notifications/list.html",
        partial_template="notifications/_items.html",
        context={
            "notifications": notifications,
            "unread_count": unread_count,
        },
    )


@login_required
def notification_mark_all_read(request: AuthenticatedRequest) -> HttpResponse:
    """Mark all notifications as read (HTMX POST)."""
    if request.method == "POST":
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)

    return notification_list(request)


@login_required
def notification_badge(request: AuthenticatedRequest) -> HttpResponse:
    """Return unread count badge (HTMX polling endpoint)."""
    from django.http import JsonResponse

    count = Notification.objects.filter(recipient=request.user, is_read=False).count()

    return JsonResponse({"count": count})
