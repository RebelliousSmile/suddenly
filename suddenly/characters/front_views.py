"""
HTMX-first views for characters (DA-1).

These views serve HTML pages and partials for the character list and detail.
DRF ViewSets in views.py remain for the JSON API.
"""

from __future__ import annotations

import json
from typing import Any

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from suddenly.core.types import AuthenticatedRequest
from suddenly.core.views import htmx_render
from suddenly.games.models import Game

from .models import Character, CharacterLink, CharacterLinkStatus, CharacterStatus
from .services import (
    build_character_queryset,
    build_transverse_actions_queryset,
    create_character_with_sheet,
)

# Payload bounds (characters:create) — reject absurdly large hidden-field
# submissions before they ever reach create_character_with_sheet.
MAX_TRAIT_SETS = 50
MAX_TRAITS_PER_TRAIT_SET = 50
MAX_ACTIONS = 50
MAX_TRAIT_REFS_PER_ACTION = 50


def _is_plain_int(value: Any) -> bool:
    """True for a genuine int — bool is a subclass of int in Python, excluded."""
    return isinstance(value, int) and not isinstance(value, bool)


def _parse_character_create_payload(raw: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate + translate the hidden ``payload`` field into the service's structures.

    ``raw`` is whatever ``json.loads`` produced — untrusted shape. Raises
    ``TypeError``/``ValueError`` on any malformed or oversized input; the caller
    (``character_create``) catches these uniformly and re-renders with a 422.
    Field-name translation: a payload TraitSet's ``name`` becomes the service's
    ``label`` (Phase 2 signature); trait references are resolved by
    ``(set_index, trait_index)`` position only, never by value.
    """
    if not isinstance(raw, dict):
        raise TypeError("payload must be an object")

    raw_trait_sets = raw.get("trait_sets", [])
    raw_actions = raw.get("actions", [])
    if not isinstance(raw_trait_sets, list) or not isinstance(raw_actions, list):
        raise TypeError("trait_sets/actions must be lists")
    if len(raw_trait_sets) > MAX_TRAIT_SETS:
        raise ValueError("too many trait sets")
    if len(raw_actions) > MAX_ACTIONS:
        raise ValueError("too many actions")

    trait_sets: list[dict[str, Any]] = []
    for trait_set_data in raw_trait_sets:
        if not isinstance(trait_set_data, dict):
            raise TypeError("trait_set must be an object")
        label = trait_set_data.get("name", "")
        if not isinstance(label, str):
            raise TypeError("trait_set name must be a string")

        raw_traits = trait_set_data.get("traits", [])
        if not isinstance(raw_traits, list):
            raise TypeError("traits must be a list")
        if len(raw_traits) > MAX_TRAITS_PER_TRAIT_SET:
            raise ValueError("too many traits")

        traits: list[dict[str, Any]] = []
        for trait_data in raw_traits:
            if not isinstance(trait_data, dict):
                raise TypeError("trait must be an object")
            trait_name = trait_data.get("name", "")
            if not isinstance(trait_name, str):
                raise TypeError("trait name must be a string")
            value = trait_data.get("value")
            if value is not None and not _is_plain_int(value):
                raise TypeError("trait value must be an int or null")
            note = trait_data.get("note", "")
            if not isinstance(note, str):
                raise TypeError("trait note must be a string")
            traits.append({"name": trait_name, "value": value, "note": note})

        trait_sets.append({"label": label, "traits": traits})

    actions: list[dict[str, Any]] = []
    for action_data in raw_actions:
        if not isinstance(action_data, dict):
            raise TypeError("action must be an object")
        action_name = action_data.get("name", "")
        condition = action_data.get("condition", "")
        outcome = action_data.get("outcome", "")
        if not isinstance(action_name, str):
            raise TypeError("action name must be a string")
        if not isinstance(condition, str) or not isinstance(outcome, str):
            raise TypeError("condition/outcome must be strings")

        raw_refs = action_data.get("trait_refs", [])
        if not isinstance(raw_refs, list):
            raise TypeError("trait_refs must be a list")
        if len(raw_refs) > MAX_TRAIT_REFS_PER_ACTION:
            raise ValueError("too many trait_refs")

        trait_refs: list[list[int]] = []
        for ref in raw_refs:
            if not isinstance(ref, list) or len(ref) != 2 or not all(_is_plain_int(i) for i in ref):
                raise TypeError("trait_refs entries must be [int, int]")
            trait_refs.append(ref)

        actions.append(
            {
                "name": action_name,
                "trait_refs": trait_refs,
                "condition": condition,
                "outcome": outcome,
            }
        )

    return trait_sets, actions


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

    # Collect all unique tags from local characters for the filter bar
    all_tags: list[str] = sorted(
        set(
            Character.objects.filter(remote=False, tags__isnull=False).values_list(
                "tags__name", flat=True
            )
        )
    )

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
    """Edit a character (creator only)."""
    character = get_object_or_404(Character, slug=slug, creator=request.user)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if not name:
            return htmx_render(
                request,
                full_template="characters/character_form.html",
                partial_template="characters/character_form.html",
                context={
                    "character": character,
                    "error": _("Name is required."),
                    "form_data": request.POST,
                },
            )
        character.name = name
        character.description = request.POST.get("description", "").strip()
        character.sheet_url = request.POST.get("sheet_url", "").strip() or None

        if request.POST.get("avatar-clear"):
            if character.avatar:
                character.avatar.delete(save=False)
            character.avatar = None
        elif "avatar" in request.FILES:
            character.avatar = request.FILES["avatar"]

        character.save(update_fields=["name", "description", "sheet_url", "avatar", "updated_at"])
        from suddenly.core.models import Tag

        character.tags.set(Tag.resolve_names(request.POST.get("tags", "")))
        return redirect(reverse("characters:detail", kwargs={"slug": character.slug}))

    return htmx_render(
        request,
        full_template="characters/character_form.html",
        partial_template="characters/character_form.html",
        context={"character": character},
    )


@login_required
def character_delete(request: AuthenticatedRequest, slug: str) -> HttpResponse:
    """Delete a character (creator only)."""
    character = get_object_or_404(Character, slug=slug, creator=request.user)
    if request.method == "POST":
        character.delete()
    return redirect(reverse("characters:list"))


@login_required
def character_delete_bulk(request: AuthenticatedRequest) -> HttpResponse:
    """Bulk delete characters (creator only)."""
    if request.method == "POST":
        slugs = request.POST.getlist("slugs")
        Character.objects.filter(slug__in=slugs, creator=request.user).delete()
    return redirect(reverse("characters:list"))


@login_required
def character_create(request: AuthenticatedRequest) -> HttpResponse:
    """Single-gesture character creation: identity + multi-concept traits + actions + sheet.

    GET renders the one-page form; ``games`` is scoped to ``request.user``'s own
    games (a PC can only originate from a game the player owns — no notion of
    "member" beyond ``owner`` exists on ``Game``). POST reads identity scalars
    directly off ``request.POST``/``request.FILES``, validates+parses the hidden
    ``payload`` JSON field (see ``_parse_character_create_payload``), then calls
    ``create_character_with_sheet`` inside its own atomic transaction. Any
    failure — malformed payload, empty name, missing/non-owned origin_game, a
    ``ValidationError`` or out-of-range ``trait_refs`` (``KeyError``) raised by
    the service — re-renders the form with ``error`` + ``form_data`` at 422;
    nothing is created on that path (the service's ``@transaction.atomic``
    guarantees the rollback).
    """
    games: QuerySet[Game] = Game.objects.filter(owner=request.user)

    if request.method != "POST":
        return render(request, "characters/character_create.html", {"games": games})

    name = request.POST.get("name", "").strip()
    description = request.POST.get("description", "").strip()
    cover_alt = request.POST.get("cover_alt", "").strip()
    cover_tone = request.POST.get("cover_tone", "").strip()
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
        raw_payload = json.loads(request.POST.get("payload", ""))
    except json.JSONDecodeError:
        return _error(str(_("Malformed payload.")))

    try:
        trait_sets, actions = _parse_character_create_payload(raw_payload)
    except (TypeError, ValueError):
        return _error(str(_("Malformed payload.")))

    try:
        character = create_character_with_sheet(
            user=request.user,
            name=name,
            description=description,
            origin_game=origin_game,
            sheet_url=sheet_url,
            avatar=avatar,
            cover_alt=cover_alt,
            cover_tone=cover_tone,
            trait_sets=trait_sets,
            actions=actions,
        )
    except (ValidationError, KeyError):
        return _error(str(_("Could not create the character.")))

    return redirect(reverse("characters:detail", kwargs={"slug": character.slug}))
