"""
SharedSequence editor views (DA-3: async editor, not CRDT).

Wireframe 09-links.md. Pessimistic locking via last_edited_by.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone

from suddenly.core.views import htmx_render

from .models import SharedSequence, SharedSequenceStatus


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
def sequence_edit(request: HttpRequest, pk: str) -> HttpResponse:
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
def sequence_propose_publish(request: HttpRequest, pk: str) -> HttpResponse:
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
def sequence_validate_publish(request: HttpRequest, pk: str) -> HttpResponse:
    """Validate (second party) and publish SharedSequence (US-19)."""
    sequence = _get_sequence_for_user(pk, request.user)

    if (
        request.method == "POST"
        and sequence.publication_proposed_by
        and sequence.publication_proposed_by != request.user
        and sequence.status == SharedSequenceStatus.DRAFT
    ):
        sequence.status = SharedSequenceStatus.PUBLISHED
        sequence.save(update_fields=["status", "updated_at"])

        # TODO: Update character status per DA-2/ADR-011
        # TODO: Create notification for both parties

    return redirect(reverse("characters:sequence_edit", kwargs={"pk": pk}))
