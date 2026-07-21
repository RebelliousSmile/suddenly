"""HTMX views for editing a character's narrative meta-model (issue B).

Reserved to the sheet's maintainer (creator or current owner). Everything here
is editorial: nothing is ever evaluated, resolved or computed. The views store
and display free-form traits and actions — no rule engine, by design.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from suddenly.core.types import AuthenticatedRequest
from suddenly.core.views import htmx_render

from .forms import ActionForm, TraitForm, TraitSetForm
from .models import Action, Character, Trait, TraitSet
from .services import build_transverse_actions_queryset


def _get_editable_character(request: AuthenticatedRequest, slug: str) -> Character | None:
    """Return the character if the user may edit its sheet, else None.

    The sheet maintainer is the creator or (for claimed/adopted PCs) the owner.
    """
    character = get_object_or_404(Character, slug=slug)
    if request.user == character.creator or (
        character.owner_id is not None and request.user == character.owner
    ):
        return character
    return None


def _render_set(
    request: AuthenticatedRequest,
    trait_set: TraitSet,
    *,
    editing_kind: str = "",
    editing_pk: object = None,
) -> str:
    """Re-render a set block. ``editing_kind``/``editing_pk`` put one row
    (``"set"`` / ``"trait"`` / ``"action"``) into inline-edit mode (#148)."""
    trait_set = TraitSet.objects.prefetch_related("traits", "actions__traits").get(pk=trait_set.pk)
    return render_to_string(
        "characters/partials/trait_set.html",
        {
            "set": trait_set,
            "character": trait_set.character,
            "editable": True,
            "editing_kind": editing_kind,
            "editing_pk": editing_pk,
        },
        request=request,
    )


@login_required
def traits_editor(request: AuthenticatedRequest, slug: str) -> HttpResponse:
    """Full-page editor listing every trait set with inline add forms."""
    character = _get_editable_character(request, slug)
    if character is None:
        return HttpResponseForbidden()

    trait_sets = character.trait_sets.prefetch_related("traits", "actions__traits")
    transverse_actions = build_transverse_actions_queryset(character)
    return htmx_render(
        request,
        full_template="characters/traits_editor.html",
        partial_template="characters/traits_editor.html",
        context={
            "character": character,
            "trait_sets": trait_sets,
            "transverse_actions": transverse_actions,
            "set_form": TraitSetForm(),
        },
    )


@login_required
def trait_set_create(request: AuthenticatedRequest, slug: str) -> HttpResponse:
    character = _get_editable_character(request, slug)
    if character is None:
        return HttpResponseForbidden()
    if request.method != "POST":
        return HttpResponseForbidden()

    form = TraitSetForm(request.POST)
    if form.is_valid():
        trait_set = form.save(commit=False)
        trait_set.character = character
        trait_set.save()
        return HttpResponse(_render_set(request, trait_set))
    return render(
        request,
        "characters/partials/trait_set_form.html",
        {"character": character, "set_form": form},
        status=422,
    )


@require_POST
@login_required
def trait_set_delete(request: AuthenticatedRequest, slug: str, set_pk: str) -> HttpResponse:
    character = _get_editable_character(request, slug)
    if character is None:
        return HttpResponseForbidden()
    trait_set = get_object_or_404(TraitSet, pk=set_pk, character=character)
    trait_set.delete()
    return HttpResponse("")


@login_required
def trait_create(request: AuthenticatedRequest, slug: str, set_pk: str) -> HttpResponse:
    character = _get_editable_character(request, slug)
    if character is None:
        return HttpResponseForbidden()
    trait_set = get_object_or_404(TraitSet, pk=set_pk, character=character)
    if request.method != "POST":
        return HttpResponseForbidden()

    form = TraitForm(request.POST)
    if form.is_valid():
        trait = form.save(commit=False)
        trait.trait_set = trait_set
        trait.save()
        return HttpResponse(_render_set(request, trait_set))
    # Re-render the whole set block (single swap target, never a broken layout).
    return HttpResponse(_render_set(request, trait_set), status=422)


@require_POST
@login_required
def trait_delete(request: AuthenticatedRequest, slug: str, trait_pk: str) -> HttpResponse:
    character = _get_editable_character(request, slug)
    if character is None:
        return HttpResponseForbidden()
    trait = get_object_or_404(
        Trait.objects.select_related("trait_set"),
        pk=trait_pk,
        trait_set__character=character,
    )
    trait_set = trait.trait_set
    trait.delete()
    return HttpResponse(_render_set(request, trait_set))


@login_required
def action_create(request: AuthenticatedRequest, slug: str, set_pk: str) -> HttpResponse:
    character = _get_editable_character(request, slug)
    if character is None:
        return HttpResponseForbidden()
    trait_set = get_object_or_404(TraitSet, pk=set_pk, character=character)
    if request.method != "POST":
        return HttpResponseForbidden()

    form = ActionForm(request.POST, trait_set=trait_set)
    if form.is_valid():
        action = form.save(commit=False)
        action.trait_set = trait_set
        action.character = trait_set.character
        action.save()
        form.save_m2m()
        return HttpResponse(_render_set(request, trait_set))
    return HttpResponse(_render_set(request, trait_set), status=422)


# ── Inline edit (#148) ─────────────────────────────────────────────────────
# GET loads an inline edit form inside the set block; POST saves and re-renders
# the plain block. All swap the single #set-<pk> target (never a broken layout).
# Dual GET/POST → internal method guard, not @require_POST (GET serves the form).


@login_required
def trait_set_card(request: AuthenticatedRequest, slug: str, set_pk: str) -> HttpResponse:
    """Plain (non-editing) re-render of a set block — the "Cancel" target."""
    character = _get_editable_character(request, slug)
    if character is None:
        return HttpResponseForbidden()
    trait_set = get_object_or_404(TraitSet, pk=set_pk, character=character)
    return HttpResponse(_render_set(request, trait_set))


@login_required
def trait_set_edit(request: AuthenticatedRequest, slug: str, set_pk: str) -> HttpResponse:
    character = _get_editable_character(request, slug)
    if character is None:
        return HttpResponseForbidden()
    trait_set = get_object_or_404(TraitSet, pk=set_pk, character=character)
    if request.method != "POST":
        return HttpResponse(
            _render_set(request, trait_set, editing_kind="set", editing_pk=trait_set.pk)
        )
    form = TraitSetForm(request.POST, instance=trait_set)
    if form.is_valid():
        form.save()
        return HttpResponse(_render_set(request, trait_set))
    return HttpResponse(
        _render_set(request, trait_set, editing_kind="set", editing_pk=trait_set.pk), status=422
    )


@login_required
def trait_edit(request: AuthenticatedRequest, slug: str, trait_pk: str) -> HttpResponse:
    character = _get_editable_character(request, slug)
    if character is None:
        return HttpResponseForbidden()
    trait = get_object_or_404(
        Trait.objects.select_related("trait_set"), pk=trait_pk, trait_set__character=character
    )
    trait_set = trait.trait_set
    if request.method != "POST":
        return HttpResponse(
            _render_set(request, trait_set, editing_kind="trait", editing_pk=trait.pk)
        )
    form = TraitForm(request.POST, instance=trait)
    if form.is_valid():
        form.save()
        return HttpResponse(_render_set(request, trait_set))
    return HttpResponse(
        _render_set(request, trait_set, editing_kind="trait", editing_pk=trait.pk), status=422
    )


@login_required
def action_edit(request: AuthenticatedRequest, slug: str, action_pk: str) -> HttpResponse:
    character = _get_editable_character(request, slug)
    if character is None:
        return HttpResponseForbidden()
    action = get_object_or_404(
        Action.objects.select_related("trait_set"), pk=action_pk, trait_set__character=character
    )
    trait_set = action.trait_set
    if trait_set is None:
        return HttpResponseForbidden()
    if request.method != "POST":
        return HttpResponse(
            _render_set(request, trait_set, editing_kind="action", editing_pk=action.pk)
        )
    form = ActionForm(request.POST, instance=action, trait_set=trait_set)
    if form.is_valid():
        form.save()
        return HttpResponse(_render_set(request, trait_set))
    return HttpResponse(
        _render_set(request, trait_set, editing_kind="action", editing_pk=action.pk), status=422
    )


@require_POST
@login_required
def action_delete(request: AuthenticatedRequest, slug: str, action_pk: str) -> HttpResponse:
    character = _get_editable_character(request, slug)
    if character is None:
        return HttpResponseForbidden()
    action = get_object_or_404(
        Action.objects.select_related("trait_set"),
        pk=action_pk,
        trait_set__character=character,
    )
    trait_set = action.trait_set
    if trait_set is None:
        # Unreachable: the queryset above joins on trait_set__character, which
        # excludes actions without a trait_set (transverse actions).
        return HttpResponseForbidden()
    action.delete()
    return HttpResponse(_render_set(request, trait_set))
