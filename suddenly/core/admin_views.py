"""
Instance administration views (US-25, US-26, wireframe 13-admin.md).

These are NOT Django admin — they're dedicated moderation pages
for instance administrators, accessible via the front-end.
"""

from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from suddenly.activitypub.models import FederatedServer, ServerStatus
from suddenly.core.views import htmx_render
from suddenly.users.models import User


@staff_member_required
def admin_dashboard(request: HttpRequest) -> HttpResponse:
    """Admin dashboard — overview of instance health (US-25)."""
    from suddenly.characters.models import Character
    from suddenly.games.models import Report

    stats = {
        "users": User.objects.filter(is_active=True, remote=False).count(),
        "reports": Report.objects.filter(status="published").count(),
        "characters": Character.objects.filter(remote=False).count(),
        "instances_federated": FederatedServer.objects.filter(
            status=ServerStatus.FEDERATED
        ).count(),
        "instances_blocked": FederatedServer.objects.filter(status=ServerStatus.BLOCKED).count(),
    }

    return htmx_render(
        request,
        full_template="admin_panel/dashboard.html",
        partial_template="admin_panel/dashboard.html",
        context={"stats": stats},
    )


@staff_member_required
def admin_instances(request: HttpRequest) -> HttpResponse:
    """Instance management — list federated/blocked instances (US-26)."""
    instances = FederatedServer.objects.order_by("status", "server_name")

    return htmx_render(
        request,
        full_template="admin_panel/instances.html",
        partial_template="admin_panel/instances.html",
        context={"instances": instances},
    )


@staff_member_required
def admin_instance_block(request: HttpRequest, pk: str) -> HttpResponse:
    """Block an instance (US-26)."""
    server = get_object_or_404(FederatedServer, pk=pk)

    if request.method == "POST":
        server.status = ServerStatus.BLOCKED
        server.save(update_fields=["status", "updated_at"])
        return redirect(reverse("admin_panel:instances"))

    return htmx_render(
        request,
        full_template="admin_panel/instance_block.html",
        partial_template="admin_panel/instance_block.html",
        context={"server": server},
    )


@staff_member_required
def admin_instance_unblock(request: HttpRequest, pk: str) -> HttpResponse:
    """Unblock an instance (US-26)."""
    server = get_object_or_404(FederatedServer, pk=pk)

    if request.method == "POST":
        server.status = ServerStatus.FEDERATED
        server.save(update_fields=["status", "updated_at"])

    return redirect(reverse("admin_panel:instances"))


@staff_member_required
def admin_users(request: HttpRequest) -> HttpResponse:
    """User management — list users with suspension controls (US-25)."""
    users = User.objects.filter(remote=False).order_by("-date_joined")[:50]

    return htmx_render(
        request,
        full_template="admin_panel/users.html",
        partial_template="admin_panel/users.html",
        context={"users_list": users},
    )


@staff_member_required
def admin_user_suspend(request: HttpRequest, pk: str) -> HttpResponse:
    """Suspend a user account (US-25)."""
    target = get_object_or_404(User, pk=pk, remote=False)

    if request.method == "POST" and target != request.user:
        target.is_active = False
        target.save(update_fields=["is_active"])

    return redirect(reverse("admin_panel:users"))
