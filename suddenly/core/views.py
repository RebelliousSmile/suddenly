"""
Core views and HTMX helpers.

DA-1: HTMX-first pattern — views return full HTML pages for normal requests
and partial HTML fragments for HTMX requests (detected via django-htmx).
"""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from suddenly.core.services import (
    get_distinct_tag_names,
    get_instance_stats,
    get_recent_public_reports,
)


def home(request: HttpRequest) -> HttpResponse:
    """Home page."""
    return render(request, "core/home.html", {"recent_reports": get_recent_public_reports()})


def explorer(request: HttpRequest) -> HttpResponse:
    """Public discovery page — characters and games tabs."""
    from suddenly.characters.models import Character, CharacterStatus
    from suddenly.characters.services import build_character_queryset
    from suddenly.games.models import Game
    from suddenly.games.services import build_game_queryset

    tab = request.GET.get("tab", "characters")
    context: dict[str, Any] = {"active_tab": tab}

    if tab == "games":
        games_qs = build_game_queryset(
            user=request.user,
            q=request.GET.get("q", ""),
            system=request.GET.get("system", ""),
            tag=request.GET.get("tag", ""),
        )
        context.update(
            {
                "games": games_qs[:24],
                "system_filter": request.GET.get("system", ""),
                "active_tag": request.GET.get("tag", ""),
                "all_tags": get_distinct_tag_names(Game),
                "query": request.GET.get("q", ""),
            }
        )
    else:
        chars_qs = build_character_queryset(
            q=request.GET.get("q", ""),
            status=request.GET.get("status", ""),
            system=request.GET.get("system", ""),
            tag=request.GET.get("tag", ""),
        )
        context.update(
            {
                "characters": chars_qs[:24],
                "query": request.GET.get("q", ""),
                "status_filter": request.GET.get("status", ""),
                "system_filter": request.GET.get("system", ""),
                "active_tag": request.GET.get("tag", ""),
                "all_tags": get_distinct_tag_names(Character),
                "statuses": CharacterStatus.choices,
            }
        )

    return render(request, "core/explorer.html", context)


def about(request: HttpRequest) -> HttpResponse:
    """Instance about page (US-31, wireframe 17)."""
    return render(request, "core/about.html", {"stats": get_instance_stats()})


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
