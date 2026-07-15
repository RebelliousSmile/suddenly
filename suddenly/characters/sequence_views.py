"""
SharedSequence editor views (DA-3: async editor, not CRDT).

Wireframe 09-links.md. Concurrent edits are last-write-wins: ``last_edited_by`` /
``last_edited_at`` record authorship for display only — there is no version or
precondition check on save, so a simultaneous edit by the other party is a lost
update by design (acceptable for the async TTRPG cadence).
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone

from suddenly.core.types import AuthenticatedRequest
from suddenly.core.views import htmx_render

from .models import SharedSequence, SharedSequenceStatus
from .services import LinkService


def _get_sequence_for_user(pk: str, user: object) -> SharedSequence:
    """Get SharedSequence ensuring user is a participant."""
    sequence = get_object_or_404(
        SharedSequence.objects.select_related(
            "link",
            "link__source",
            "link__target",
            "link__link_request",
            "link__link_request__requester",
            "link__link_request__target_character__creator",
            "last_edited_by",
            "publication_proposed_by",
        ),
        pk=pk,
    )
    # Only participants can access
    lr = sequence.link.link_request
    if lr and (lr.requester == user or lr.target_character.creator == user):
        return sequence
    # Also allow if user owns source or target character
    if sequence.link.source.owner == user or sequence.link.target.creator == user:
        return sequence
    from django.http import Http404

    raise Http404


@login_required
def sequence_edit(request: AuthenticatedRequest, pk: str) -> HttpResponse:
    """SharedSequence editor (US-18)."""
    sequence = _get_sequence_for_user(pk, request.user)

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        content = request.POST.get("content", "").strip()

        sequence.title = title
        sequence.content = content
        sequence.last_edited_by = request.user
        sequence.last_edited_at = timezone.now()
        sequence.save(
            update_fields=["title", "content", "last_edited_by", "last_edited_at", "updated_at"]
        )

        return htmx_render(
            request,
            full_template="characters/sequence_edit.html",
            partial_template="characters/sequence_edit.html",
            context={"sequence": sequence, "saved": True},
        )

    return htmx_render(
        request,
        full_template="characters/sequence_edit.html",
        partial_template="characters/sequence_edit.html",
        context={"sequence": sequence},
    )


@login_required
def sequence_suggest_opening(request: AuthenticatedRequest, pk: str) -> HttpResponse:
    """Suggest a neutral opening for an empty shared sequence (#127).

    A third voice, belonging to neither player, to break the blank-page-for-two.
    Returns an inline suggestion (never auto-inserted); degrades to a discreet
    "unavailable" note if the hub is disabled or unreachable (#88).
    """
    from suddenly.muses.client import MusesClient, SessionContext
    from suddenly.muses.credits import debit, has_credits
    from suddenly.muses.exceptions import MusesError

    from .muses_context import anchor_reports, axial_tags, character_sheet

    sequence = _get_sequence_for_user(pk, request.user)

    # Only offered while the sequence is an empty draft — the blank page.
    if (
        request.method != "POST"
        or sequence.status != SharedSequenceStatus.DRAFT
        or sequence.content.strip()
    ):
        return redirect(reverse("characters:sequence_edit", kwargs={"pk": pk}))

    def _render(suggestion: dict[str, str] | None, *, no_credits: bool = False) -> HttpResponse:
        return htmx_render(
            request,
            full_template="characters/_sequence_suggestion.html",
            partial_template="characters/_sequence_suggestion.html",
            context={"sequence": sequence, "suggestion": suggestion, "no_credits": no_credits},
        )

    # Gate: service must be active (per-user switch + instance hub)...
    if not (getattr(request.user, "muses_enabled", False) and MusesClient.is_enabled()):
        return _render(None)
    # ...and the account must have credits left.
    if not has_credits(request.user):
        return _render(None, no_credits=True)

    source = sequence.link.source
    target = sequence.link.target
    context = SessionContext(
        characters=[character_sheet(source), character_sheet(target)],
        link_type=sequence.link.type,
        reports=anchor_reports(target),  # the NPC's anchor scene
        tags=sorted(set(axial_tags(source)) | set(axial_tags(target))),
    )

    suggestion: dict[str, str] | None = None
    try:
        result = MusesClient().suggest(context, feature="opening")
        kind = str(result.get("kind", "narration"))
        text = str(result.get("text", "")).strip()
        # The Muse never speaks for a character it does not control (#127):
        # a dialogue answer is downgraded to narration for display.
        if kind == "dialogue":
            kind = "narration"
        if text:
            suggestion = {"kind": kind, "text": text}
    except MusesError:
        suggestion = None  # degraded mode: render the discreet unavailable note

    # Debit one credit only on a real suggestion (never in degraded mode, #88).
    if suggestion:
        debit(request.user)

    return _render(suggestion)


@login_required
def sequence_propose_publish(request: AuthenticatedRequest, pk: str) -> HttpResponse:
    """Propose publication of SharedSequence (US-19)."""
    sequence = _get_sequence_for_user(pk, request.user)

    if request.method == "POST" and sequence.status == SharedSequenceStatus.DRAFT:
        sequence.publication_proposed_by = request.user
        sequence.publication_proposed_at = timezone.now()
        sequence.save(
            update_fields=[
                "publication_proposed_by",
                "publication_proposed_at",
                "updated_at",
            ]
        )

    return redirect(reverse("characters:sequence_edit", kwargs={"pk": pk}))


@login_required
def sequence_validate_publish(request: AuthenticatedRequest, pk: str) -> HttpResponse:
    """Validate (second party) and publish SharedSequence (US-19)."""
    sequence = _get_sequence_for_user(pk, request.user)

    if (
        request.method == "POST"
        and sequence.publication_proposed_by
        and sequence.publication_proposed_by != request.user
        and sequence.status == SharedSequenceStatus.DRAFT
    ):
        # Character status + link were already set at acceptance (DEC-035).
        # Publishing finalizes the co-created sequence and notifies both parties.
        LinkService.publish_sequence(sequence, request.user)

    return redirect(reverse("characters:sequence_edit", kwargs={"pk": pk}))
