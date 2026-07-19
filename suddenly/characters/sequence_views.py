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

    # A blank DRAFT sequence gets a social Offer (sequence_opening) addressed
    # to the current viewer's followers, to help propose an opening (Epic B,
    # #132). Idempotent: returns the existing open offer once one exists.
    offer = None
    if sequence.status == SharedSequenceStatus.DRAFT and not sequence.content.strip():
        from suddenly.offers.models import OfferKind
        from suddenly.offers.services import OfferService

        offer = OfferService.open_offer(
            kind=OfferKind.SEQUENCE_OPENING, carrier=sequence, emitter=request.user
        )

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
            context={"sequence": sequence, "saved": True, "offer": offer},
        )

    return htmx_render(
        request,
        full_template="characters/sequence_edit.html",
        partial_template="characters/sequence_edit.html",
        context={"sequence": sequence, "offer": offer},
    )


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
