"""
Core views and HTMX helpers.

DA-1: HTMX-first pattern — views return full HTML pages for normal requests
and partial HTML fragments for HTMX requests (detected via django-htmx).
"""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from suddenly.core.services import get_recent_public_reports


def home(request: HttpRequest) -> HttpResponse:
    """Home page."""
    return render(request, "core/home.html", {"recent_reports": get_recent_public_reports()})


def about(request: HttpRequest) -> HttpResponse:
    """Instance about page (US-31, wireframe 17)."""
    from suddenly.activitypub.models import FederatedServer
    from suddenly.characters.models import Character
    from suddenly.games.models import Report
    from suddenly.users.models import User

    stats = {
        "users": User.objects.filter(is_active=True, remote=False).count(),
        "reports": Report.objects.filter(status="published").count(),
        "characters": Character.objects.filter(remote=False).count(),
        "instances": FederatedServer.objects.exclude(status="BLOCKED").count(),
    }

    return render(request, "core/about.html", {"stats": stats})


def htmx_render(
    request: HttpRequest,
    full_template: str,
    partial_template: str,
    context: dict[str, Any] | None = None,
) -> HttpResponse:
    """Render full page or HTMX partial based on request type.

    DA-1 pattern: if the request comes from HTMX (hx-get/hx-post),
    return the partial template (fragment). Otherwise return the full
    page that wraps the partial.

    Usage in views:
        return htmx_render(
            request,
            full_template="characters/list.html",
            partial_template="characters/_list_results.html",
            context={"characters": qs},
        )
    """
    template = partial_template if getattr(request, "htmx", False) else full_template
    return render(request, template, context or {})
