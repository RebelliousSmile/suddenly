"""
Instance administration views (US-25, US-26, wireframe 13-admin.md).

These are NOT Django admin — they're dedicated moderation pages
for instance administrators, accessible via the front-end.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from suddenly.activitypub.models import FederatedServer, ServerStatus
from suddenly.core.decorators import admin_required
from suddenly.core.models import InstanceSettings
from suddenly.core.types import AuthenticatedRequest
from suddenly.core.views import htmx_render
from suddenly.users.models import User


@admin_required
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
        full_template="gmh/dashboard.html",
        partial_template="gmh/dashboard.html",
        context={"stats": stats},
    )


@admin_required
def admin_instances(request: HttpRequest) -> HttpResponse:
    """Instance management — list federated/blocked instances (US-26)."""
    instances = FederatedServer.objects.order_by("status", "server_name")

    return htmx_render(
        request,
        full_template="gmh/instances.html",
        partial_template="gmh/instances.html",
        context={"instances": instances},
    )


@admin_required
def admin_instance_block(request: HttpRequest, pk: str) -> HttpResponse:
    """Block an instance (US-26)."""
    server = get_object_or_404(FederatedServer, pk=pk)

    if request.method == "POST":
        server.status = ServerStatus.BLOCKED
        server.save(update_fields=["status", "updated_at"])
        return redirect(reverse("gmh:instances"))

    return htmx_render(
        request,
        full_template="gmh/instance_block.html",
        partial_template="gmh/instance_block.html",
        context={"server": server},
    )


@admin_required
def admin_instance_unblock(request: HttpRequest, pk: str) -> HttpResponse:
    """Unblock an instance (US-26)."""
    server = get_object_or_404(FederatedServer, pk=pk)

    if request.method == "POST":
        server.status = ServerStatus.FEDERATED
        server.save(update_fields=["status", "updated_at"])

    return redirect(reverse("gmh:instances"))


@admin_required
def admin_users(request: HttpRequest) -> HttpResponse:
    """User management — list users with suspension controls (US-25)."""
    users = User.objects.filter(remote=False).order_by("-date_joined")[:50]

    return htmx_render(
        request,
        full_template="gmh/users.html",
        partial_template="gmh/users.html",
        context={"users_list": users},
    )


@admin_required
def admin_user_suspend(request: HttpRequest, pk: str) -> HttpResponse:
    """Suspend a user account (US-25)."""
    target = get_object_or_404(User, pk=pk, remote=False)

    if request.method == "POST" and target != request.user:
        target.is_active = False
        target.save(update_fields=["is_active"])

    return redirect(reverse("gmh:users"))


@admin_required
def admin_reports(request: HttpRequest) -> HttpResponse:
    """Moderation queue — pending user reports (#136, DEC-F4)."""
    from suddenly.core.models import UserReport, UserReportStatus

    reports = (
        UserReport.objects.filter(status=UserReportStatus.PENDING)
        .select_related("reporter", "reported_user")
        .order_by("-created_at")
    )

    return htmx_render(
        request,
        full_template="gmh/reports.html",
        partial_template="gmh/reports.html",
        context={"reports": reports},
    )


@require_POST
@admin_required
def admin_report_dismiss(request: AuthenticatedRequest, pk: str) -> HttpResponse:
    """Dismiss a pending report without blocking the reported user (#136, DEC-F4)."""
    from django.utils import timezone

    from suddenly.core.models import UserReport, UserReportStatus

    report = get_object_or_404(UserReport, pk=pk, status=UserReportStatus.PENDING)
    report.status = UserReportStatus.DISMISSED
    report.handled_by = request.user
    report.handled_at = timezone.now()
    report.save(update_fields=["status", "handled_by", "handled_at", "updated_at"])

    return redirect(reverse("gmh:reports"))


@require_POST
@admin_required
def admin_user_block(request: AuthenticatedRequest, pk: str) -> HttpResponse:
    """Block the reported user of a pending report and resolve it (#136, DEC-F4).

    ``pk`` is the ``UserReport`` primary key (not the user's) — the block
    action always originates from a specific report in the queue, and
    resolving that report atomically with the ban is the whole point of
    ``block_user(..., report=...)`` (DEC-F3).
    """
    from suddenly.core.models import UserReport, UserReportStatus
    from suddenly.core.moderation import block_user

    report = get_object_or_404(UserReport, pk=pk, status=UserReportStatus.PENDING)
    block_user(report.reported_user, by=request.user, report=report)

    return redirect(reverse("gmh:reports"))


@require_POST
@admin_required
def admin_user_unblock(request: HttpRequest, pk: str) -> HttpResponse:
    """Lift the instance-interaction ban on a user (#136, DEC-F4 — reversibility).

    ``pk`` is the ``User`` primary key — unblocking is not tied to any
    specific report (a user may accumulate several resolved reports), so it
    lives alongside ``admin_user_suspend`` on the users list rather than on
    the reports queue.
    """
    from suddenly.core.moderation import unblock_user

    target = get_object_or_404(User, pk=pk, remote=False)
    unblock_user(target)

    return redirect(reverse("gmh:users"))


@admin_required
def instance_settings(request: HttpRequest) -> HttpResponse:
    """Instance settings — view and update instance-wide configuration."""
    instance = InstanceSettings.get()

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if not name:
            messages.error(request, "Instance name is required.")
        else:
            instance.name = name
            instance.description = request.POST.get("description", "").strip()
            instance.language = request.POST.get("language", instance.language)
            instance.registrations_open = "registrations_open" in request.POST
            instance.save()
            messages.success(request, "Instance settings saved.")
            return redirect(reverse("gmh:instance_settings"))

    return render(
        request,
        "gmh/instance_settings.html",
        {
            "instance": instance,
            "languages": settings.LANGUAGES,
        },
    )
