"""
Core views and HTMX helpers.

DA-1: HTMX-first pattern — views return full HTML pages for normal requests
and partial HTML fragments for HTMX requests (detected via django-htmx).
"""

from __future__ import annotations

from typing import Any, cast

from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from suddenly.core.services import (
    get_distinct_tag_names,
    get_instance_quotes,
    get_instance_stats,
    get_recent_public_reports,
)
from suddenly.core.types import AuthenticatedRequest


def switch_language(request: HttpRequest) -> HttpResponse:
    """Django's ``set_language`` + persistence for authenticated users.

    The switcher cookie is honoured by LocaleMiddleware and respected by
    InstanceLanguageMiddleware (which only supplies the instance *default*).
    For an authenticated user the choice is also saved to
    ``interface_language`` so UserLanguageMiddleware applies it from the very
    next request — otherwise the stored preference would silently override
    every switch.
    """
    from django.conf import settings
    from django.views.i18n import set_language as django_set_language

    response = django_set_language(request)
    user = request.user
    if request.method == "POST" and user.is_authenticated:
        lang = request.POST.get("language", "")
        if lang in dict(settings.LANGUAGES):
            user.interface_language = lang
            user.save(update_fields=["interface_language"])
    return response


def home(request: HttpRequest) -> HttpResponse:
    """
    Home page.

    Mastodon-like behaviour (Front #1): a single canonical ``/`` URL with two
    renders depending on the session. Authenticated users get their feed
    (delegated to ``feed_home``, keeping ``/`` as the displayed URL); anonymous
    visitors get the marketing vitrine enriched with instance stats (Front #2)
    and a few promotable citations ("ce qu'on y dit") from the double-locked
    queryset.
    """
    if request.user.is_authenticated:
        from suddenly.core.feed_views import feed_home

        return feed_home(cast(AuthenticatedRequest, request))

    return render(
        request,
        "core/home.html",
        {
            "recent_reports": get_recent_public_reports(),
            "stats": get_instance_stats(),
            "instance_quotes": get_instance_quotes(3),
        },
    )


def quotes(request: HttpRequest) -> HttpResponse:
    """Public wall of citations (/citations) — no authentication (prompt §4.2).

    Every card is promotable: released report AND public, non-expired quote. The
    view never re-expresses the wall — it starts from ``promotable()``.
    """
    from suddenly.characters.models import Quote

    page_obj = Paginator(Quote.objects.promotable(), 24).get_page(request.GET.get("page"))
    return render(
        request,
        "core/quotes.html",
        {"page_obj": page_obj, "quotes": page_obj.object_list},
    )


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
            tag=request.GET.get("tag", ""),
        )
        context.update(
            {
                "characters": chars_qs[:24],
                "query": request.GET.get("q", ""),
                "status_filter": request.GET.get("status", ""),
                "active_tag": request.GET.get("tag", ""),
                "all_tags": get_distinct_tag_names(Character),
                "statuses": CharacterStatus.choices,
            }
        )

    return render(request, "core/explorer.html", context)


def about(request: HttpRequest) -> HttpResponse:
    """Instance about page (US-31, wireframe 17)."""
    return render(request, "core/about.html", {"stats": get_instance_stats()})


def directory(request: HttpRequest) -> HttpResponse:
    """Public profile directory — local, active members of this instance.

    Remote (federated) accounts are excluded: they are discovered through
    federation, not listed as members here.
    """
    from suddenly.users.models import User

    members = User.objects.filter(remote=False, is_active=True).order_by("display_name", "username")
    paginator = Paginator(members, 24)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "core/directory.html",
        {"page_obj": page_obj, "total": paginator.count},
    )


def privacy(request: HttpRequest) -> HttpResponse:
    """Privacy policy — static content page."""
    return render(request, "core/privacy.html")


def apps(request: HttpRequest) -> HttpResponse:
    """Compatible applications — static content page for the Fediverse."""
    return render(request, "core/apps.html")


def shortcuts(request: HttpRequest) -> HttpResponse:
    """Keyboard shortcuts reference — mirrors the global handler in main.js."""
    return render(request, "core/shortcuts.html")


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
