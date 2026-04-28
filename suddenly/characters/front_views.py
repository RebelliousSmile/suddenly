"""
HTMX-first views for characters (DA-1).

These views serve HTML pages and partials for the character list and detail.
DRF ViewSets in views.py remain for the JSON API.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from suddenly.core.types import AuthenticatedRequest
from suddenly.core.views import htmx_render

from .models import Character, CharacterStatus


def character_list(request: HttpRequest) -> HttpResponse:
    """Character list with FTS search and filters (US-07)."""
    qs = _build_character_queryset(request)

    return htmx_render(
        request,
        full_template="characters/list.html",
        partial_template="characters/_list_results.html",
        context={
            "characters": qs[:24],
            "query": request.GET.get("q", ""),
            "status_filter": request.GET.get("status", ""),
            "system_filter": request.GET.get("system", ""),
            "statuses": CharacterStatus.choices,
        },
    )


def character_detail(request: HttpRequest, slug: str) -> HttpResponse:
    """Character detail page (US-06)."""
    character = get_object_or_404(
        Character.objects.select_related("creator", "owner", "origin_game", "parent"),
        slug=slug,
    )

    appearances = character.appearances.select_related(
        "report", "report__game", "report__author"
    ).order_by("-report__published_at")[:20]

    quotes = character.quotes.filter(visibility="public").order_by("-created_at")[:10]

    # Follow state + pending request for current user
    context: dict[str, object] = {
        "character": character,
        "appearances": appearances,
        "quotes": quotes,
    }

    if request.user.is_authenticated:
        from .models import LinkRequest, LinkRequestStatus

        pending = LinkRequest.objects.filter(
            requester=request.user,
            target_character=character,
            status__in=[LinkRequestStatus.PENDING, LinkRequestStatus.QUEUED],
        ).first()
        context["pending_request"] = pending

    return htmx_render(
        request,
        full_template="characters/detail.html",
        partial_template="characters/detail.html",
        context=context,
    )


def character_search(request: HttpRequest) -> HttpResponse:
    """HTMX endpoint for live character search (partial only)."""
    qs = _build_character_queryset(request)

    return htmx_render(
        request,
        full_template="characters/_list_results.html",
        partial_template="characters/_list_results.html",
        context={
            "characters": qs[:24],
            "query": request.GET.get("q", ""),
        },
    )


def _build_character_queryset(request: HttpRequest) -> QuerySet[Character]:
    """Build filtered character queryset from request params."""
    qs = (
        Character.objects.filter(remote=False)
        .select_related("creator", "owner", "origin_game")
        .order_by("-created_at")
    )

    # Status filter
    status = request.GET.get("status", "")
    if status and status in CharacterStatus.values:
        qs = qs.filter(status=status)

    # Game system filter
    system = request.GET.get("system", "").strip()
    if system:
        qs = qs.filter(origin_game__game_system__icontains=system)

    # FTS search (uses GIN index from T13)
    q = request.GET.get("q", "").strip()
    if q:
        search_query = SearchQuery(q, config="french")
        search_vector = SearchVector("name", weight="A", config="french") + SearchVector(
            "description", weight="B", config="french"
        )
        qs = (
            qs.annotate(rank=SearchRank(search_vector, search_query))
            .filter(rank__gt=0.01)
            .order_by("-rank")
        )

    return qs


@login_required
def quote_add(request: AuthenticatedRequest, slug: str) -> HttpResponse:
    """Add a quote to a character (US-08). HTMX partial."""
    character = get_object_or_404(Character, slug=slug)

    if request.method == "POST":
        from .models import Quote, QuoteVisibility

        content = request.POST.get("content", "").strip()
        context_text = request.POST.get("context", "").strip()
        cw = request.POST.get("content_warning", "").strip()
        visibility = request.POST.get("visibility", QuoteVisibility.PUBLIC)

        if len(content) < 2:
            return render(
                request,
                "characters/_quote_form.html",
                {
                    "character": character,
                    "error": "La citation doit faire au moins 2 caractères.",
                    "form_data": request.POST,
                },
                status=422,
            )

        quote = Quote.objects.create(
            content=content,
            context=context_text,
            content_warning=cw,
            visibility=visibility,
            character=character,
            author=request.user,
        )
        return render(request, "characters/_quote_card.html", {"quote": quote})

    # GET: return the form partial
    return render(
        request,
        "characters/_quote_form.html",
        {"character": character},
    )
