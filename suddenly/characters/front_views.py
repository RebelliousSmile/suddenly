"""
HTMX-first views for characters (DA-1).

These views serve HTML pages and partials for the character list and detail.
DRF ViewSets in views.py remain for the JSON API.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from suddenly.core.services import get_distinct_tag_names
from suddenly.core.types import AuthenticatedRequest
from suddenly.core.views import htmx_render
from suddenly.games.models import Game

from .models import Character, CharacterLink, CharacterLinkStatus, CharacterStatus
from .services import (
    build_character_queryset,
    build_transverse_actions_queryset,
    character_has_posts,
    create_character_with_sheet,
    suggested_characters_to_link,
)


def character_list(request: HttpRequest) -> HttpResponse:
    """Character list with FTS search and filters (US-07)."""
    qs = build_character_queryset(
        q=request.GET.get("q", ""),
        status=request.GET.get("status", ""),
        tag=request.GET.get("tag", ""),
    )

    default_bg = ""
    first_character = None
    if request.user.is_authenticated:
        if request.user.default_character_background:
            default_bg = request.user.default_character_background.url
        first_character = (
            Character.objects.filter(
                origin_game__owner=request.user,
                origin_game__remote=False,
            )
            .order_by("name")
            .first()
        )

    # Distinct tags for the filter bar — cached + DB-distinct via the shared
    # service (avoids the uncached full-scan + Python set() this used to do).
    all_tags = get_distinct_tag_names(Character)

    return htmx_render(
        request,
        full_template="characters/list.html",
        partial_template="characters/_list_results.html",
        context={
            "characters": qs[:24],
            "query": request.GET.get("q", ""),
            "status_filter": request.GET.get("status", ""),
            "statuses": CharacterStatus.choices,
            "default_bg": default_bg,
            "active_tag": request.GET.get("tag", ""),
            "all_tags": all_tags,
            "first_character": first_character,
        },
    )


def character_card(request: HttpRequest, slug: str) -> HttpResponse:
    """The hover-card of a character (tooltip content), lazy-loaded over HTMX.

    Public — character pages are public. Rendered inside the popover of a
    character link on first hover; kept small (identity, status, one-line pitch,
    and the claim/adopt/fork affordances when the character is available).
    """
    character = get_object_or_404(
        Character.objects.select_related("origin_game", "owner"),
        slug=slug,
    )
    return render(request, "characters/_character_card.html", {"character": character})


def character_detail(request: HttpRequest, slug: str) -> HttpResponse:
    """Character detail page (US-06)."""
    character = get_object_or_404(
        Character.objects.select_related("creator", "owner", "origin_game", "parent"),
        slug=slug,
    )

    appearances = character.appearances.select_related(
        "report", "report__game", "report__author"
    ).order_by("-report__published_at")[:20]

    # §4.4: the character's citations, behind the double lock (released report +
    # public quote). The wall filter is never re-expressed here.
    from .models import Quote

    quotes = Quote.objects.promotable().filter(character=character).order_by("-created_at")[:10]

    # Narrative meta-model (issues A/C): displayed, never evaluated.
    trait_sets = character.trait_sets.prefetch_related("traits", "actions__traits")

    # Cross-concept actions (trait_set=None) — "Actions transverses" block.
    transverse_actions = build_transverse_actions_queryset(character)

    # The sheet maintainer (creator or owner) may edit traits.
    can_edit_traits = request.user.is_authenticated and (
        request.user == character.creator
        or (character.owner_id is not None and request.user == character.owner)
    )

    # Follow state + pending request for current user
    context: dict[str, object] = {
        "character": character,
        "appearances": appearances,
        "quotes": quotes,
        "trait_sets": trait_sets,
        "transverse_actions": transverse_actions,
        "can_edit_traits": can_edit_traits,
    }

    if request.user.is_authenticated:
        from .models import LinkRequest, LinkRequestStatus

        pending = LinkRequest.objects.filter(
            requester=request.user,
            target_character=character,
            status__in=[LinkRequestStatus.PENDING, LinkRequestStatus.QUEUED],
        ).first()
        context["pending_request"] = pending

        # Links for revoke UI (US-16)
        context["target_link"] = (
            CharacterLink.objects.filter(target=character, status=CharacterLinkStatus.ACTIVE)
            .select_related("source")
            .first()
        )
        context["source_link"] = CharacterLink.objects.filter(
            source=character, status=CharacterLinkStatus.ACTIVE
        ).first()

    # Follow state (Epic C, #133) — guarded so the creator/owner never sees
    # a follow button on their own character (self-follow, matching the
    # Game/User detail views' pattern).
    is_following = False
    if request.user.is_authenticated and request.user not in (
        character.creator,
        character.owner,
    ):
        from django.contrib.contenttypes.models import ContentType

        from .models import Follow

        ct = ContentType.objects.get_for_model(Character)
        is_following = Follow.objects.filter(
            follower=request.user, content_type=ct, object_id=character.pk
        ).exists()
    context["is_following"] = is_following

    # Direct-message entry point (Epic E, #135, DEC-E7) — read-only, gated by
    # mutuality; never writes a Follow. Targets the character's owner (the
    # player controlling it), not the creator.
    dm_recipient = None
    if (
        request.user.is_authenticated
        and character.owner is not None
        and request.user != character.owner
    ):
        from .models import Follow

        if Follow.objects.are_mutual(request.user, character.owner):
            dm_recipient = character.owner
    context["dm_recipient"] = dm_recipient

    return htmx_render(
        request,
        full_template="characters/detail.html",
        partial_template="characters/detail.html",
        context=context,
    )


def character_search(request: HttpRequest) -> HttpResponse:
    """HTMX endpoint for live character search (partial only)."""
    qs = build_character_queryset(
        q=request.GET.get("q", ""),
        status=request.GET.get("status", ""),
        tag=request.GET.get("tag", ""),
    )

    default_bg = ""
    if request.user.is_authenticated and request.user.default_character_background:
        default_bg = request.user.default_character_background.url

    return htmx_render(
        request,
        full_template="characters/_list_results.html",
        partial_template="characters/_list_results.html",
        context={
            "characters": qs[:24],
            "query": request.GET.get("q", ""),
            "default_bg": default_bg,
            "active_tag": request.GET.get("tag", ""),
        },
    )


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


@login_required
def character_edit(request: AuthenticatedRequest, slug: str) -> HttpResponse:
    """Edit a character (creator only).

    The character's game (``origin_game``) is editable here — scoped to games the
    editor owns, exactly like creation — but **locked once the character has
    posts** (#154): re-homing an active character would move its AP federation
    home and split its activity. The lock is enforced server-side, never trusting
    the disabled ``<select>``.
    """
    character = get_object_or_404(Character, slug=slug, creator=request.user)

    # Owned games scope the picker (mirror of character_create); the lock freezes
    # origin_game once the character is the actor of at least one post.
    games = Game.objects.filter(owner=request.user)
    game_locked = character_has_posts(character)

    def _render_form(error: object = None, form_data: object = None) -> HttpResponse:
        return htmx_render(
            request,
            full_template="characters/character_form.html",
            partial_template="characters/character_form.html",
            context={
                "character": character,
                "games": games,
                "game_locked": game_locked,
                "error": error,
                "form_data": form_data,
            },
        )

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if not name:
            return _render_form(error=_("Name is required."), form_data=request.POST)

        update_fields = [
            "name",
            "description",
            "background",
            "secrets",
            "sheet_url",
            "avatar",
            "updated_at",
        ]

        # Game change — only when unlocked. A locked character ignores any posted
        # origin_game (server guard). An empty value keeps the current game
        # (origin_game is non-null; never overwrite it with nothing).
        if not game_locked:
            origin_game_pk = request.POST.get("origin_game", "").strip()
            if origin_game_pk and origin_game_pk != str(character.origin_game_id):
                try:
                    character.origin_game = games.get(pk=origin_game_pk)
                except (Game.DoesNotExist, ValidationError, ValueError):
                    return _render_form(error=_("Choose a game you own."), form_data=request.POST)
                update_fields.append("origin_game")

        character.name = name
        character.description = request.POST.get("description", "").strip()
        character.background = request.POST.get("background", "").strip()
        character.secrets = request.POST.get("secrets", "").strip()
        character.sheet_url = request.POST.get("sheet_url", "").strip() or None

        if request.POST.get("avatar-clear"):
            if character.avatar:
                character.avatar.delete(save=False)
            character.avatar = None
        elif "avatar" in request.FILES:
            character.avatar = request.FILES["avatar"]

        character.save(update_fields=update_fields)
        from suddenly.core.models import Tag

        character.tags.set(Tag.resolve_names(request.POST.get("tags", "")))
        return redirect(reverse("characters:detail", kwargs={"slug": character.slug}))

    return _render_form()


@require_POST
@login_required
def character_delete(request: AuthenticatedRequest, slug: str) -> HttpResponse:
    """Delete a character (creator only)."""
    character = get_object_or_404(Character, slug=slug, creator=request.user)
    character.delete()
    return redirect(reverse("characters:list"))


@require_POST
@login_required
def character_delete_bulk(request: AuthenticatedRequest) -> HttpResponse:
    """Bulk delete characters (creator only)."""
    slugs = request.POST.getlist("slugs")
    Character.objects.filter(slug__in=slugs, creator=request.user).delete()
    return redirect(reverse("characters:list"))


@login_required
def character_create(request: AuthenticatedRequest) -> HttpResponse:
    """Identity-first character creation (#148).

    GET renders the identity form; ``games`` is scoped to ``request.user``'s own
    games (a PC can only originate from a game the player owns). POST reads the
    identity scalars off ``request.POST``/``request.FILES`` and creates the
    character with an empty sheet, then redirects to the traits editor — traits
    and actions are added per row there (persisted and editable one at a time),
    replacing the former in-memory ``payload`` batch. On empty name or a
    missing/non-owned origin game, re-renders the form with ``error`` +
    ``form_data`` at 422.
    """
    games: QuerySet[Game] = Game.objects.filter(owner=request.user)

    if request.method != "POST":
        return render(
            request,
            "characters/character_create.html",
            {
                "games": games,
                "preselected_game": request.GET.get("game", ""),
                "link_suggestions": suggested_characters_to_link(request.user),
            },
        )

    name = request.POST.get("name", "").strip()
    description = request.POST.get("description", "").strip()
    background = request.POST.get("background", "").strip()
    secrets = request.POST.get("secrets", "").strip()
    cover_alt = request.POST.get("cover_alt", "").strip()
    sheet_url = request.POST.get("sheet_url", "").strip()
    avatar = request.FILES.get("avatar")
    origin_game_pk = request.POST.get("origin_game", "").strip()

    def _error(message: str) -> HttpResponse:
        return render(
            request,
            "characters/character_create.html",
            {"games": games, "error": message, "form_data": request.POST},
            status=422,
        )

    if not name:
        return _error(str(_("Name is required.")))

    if not origin_game_pk:
        return _error(str(_("Origin game is required.")))

    try:
        origin_game = games.get(pk=origin_game_pk)
    except (Game.DoesNotExist, ValidationError, ValueError):
        return _error(str(_("Origin game is required.")))

    try:
        character = create_character_with_sheet(
            user=request.user,
            name=name,
            description=description,
            background=background,
            secrets=secrets,
            origin_game=origin_game,
            sheet_url=sheet_url,
            avatar=avatar,
            cover_alt=cover_alt,
            trait_sets=[],
            actions=[],
        )
    except ValidationError:
        return _error(str(_("Could not create the character.")))

    # Land on the per-row traits editor to build the sheet (#148).
    return redirect(reverse("characters:traits_editor", kwargs={"slug": character.slug}))
