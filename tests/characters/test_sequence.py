"""
Tests for the SharedSequence double-validation publish workflow (US-19).

Covers audit gap #3 (session 2026-05-17): ``sequence_propose_publish`` and
``sequence_validate_publish`` implement a two-party publication handshake that
had no tests.

Rules under test:
- proposing sets ``publication_proposed_by`` and keeps the sequence in DRAFT
- proposing by A then validating by the *other* party publishes it
- validating by the *same* party that proposed does NOT publish (double-validation)
- proposing on an already-published sequence is a no-op
"""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client
from django.urls import reverse

from suddenly.characters.models import (
    Character,
    LinkRequest,
    LinkType,
    SharedSequence,
    SharedSequenceStatus,
)
from suddenly.characters.services import LinkService
from suddenly.users.models import User


@pytest.fixture
def sequence(db: Any, user: User, other_user: User, character: Character) -> SharedSequence:
    """
    A DRAFT SharedSequence from an accepted adopt link.

    Participants: ``other_user`` (requester) and ``user`` (target creator).
    """
    request = LinkRequest.objects.create(
        type=LinkType.ADOPT,
        requester=other_user,
        target_character=character,
        message="I'll adopt",
    )
    link = LinkService.accept_request(request)
    return link.shared_sequence


class TestProposePublish:
    def test_propose_sets_proposer_and_stays_draft(
        self, db: Any, client: Client, user: User, sequence: SharedSequence
    ) -> None:
        client.force_login(user)

        resp = client.post(reverse("characters:sequence_propose", kwargs={"pk": sequence.pk}))

        assert resp.status_code == 302
        sequence.refresh_from_db()
        assert sequence.publication_proposed_by == user
        assert sequence.publication_proposed_at is not None
        assert sequence.status == SharedSequenceStatus.DRAFT

    def test_propose_on_published_is_noop(
        self, db: Any, client: Client, user: User, sequence: SharedSequence
    ) -> None:
        sequence.status = SharedSequenceStatus.PUBLISHED
        sequence.save(update_fields=["status"])

        client.force_login(user)
        client.post(reverse("characters:sequence_propose", kwargs={"pk": sequence.pk}))

        sequence.refresh_from_db()
        assert sequence.publication_proposed_by is None
        assert sequence.status == SharedSequenceStatus.PUBLISHED


class TestValidatePublish:
    def test_propose_by_a_validate_by_b_publishes(
        self,
        db: Any,
        client: Client,
        user: User,
        other_user: User,
        sequence: SharedSequence,
    ) -> None:
        # A (user, the creator) proposes.
        client.force_login(user)
        client.post(reverse("characters:sequence_propose", kwargs={"pk": sequence.pk}))

        # B (other_user, the requester) validates.
        client.force_login(other_user)
        resp = client.post(reverse("characters:sequence_publish", kwargs={"pk": sequence.pk}))

        assert resp.status_code == 302
        sequence.refresh_from_db()
        assert sequence.status == SharedSequenceStatus.PUBLISHED

    def test_propose_and_validate_by_same_party_does_not_publish(
        self, db: Any, client: Client, user: User, sequence: SharedSequence
    ) -> None:
        client.force_login(user)
        client.post(reverse("characters:sequence_propose", kwargs={"pk": sequence.pk}))
        # Same user tries to validate their own proposal.
        client.post(reverse("characters:sequence_publish", kwargs={"pk": sequence.pk}))

        sequence.refresh_from_db()
        assert sequence.status == SharedSequenceStatus.DRAFT

    def test_validate_without_proposal_does_not_publish(
        self, db: Any, client: Client, other_user: User, sequence: SharedSequence
    ) -> None:
        client.force_login(other_user)
        client.post(reverse("characters:sequence_publish", kwargs={"pk": sequence.pk}))

        sequence.refresh_from_db()
        assert sequence.status == SharedSequenceStatus.DRAFT

    def test_non_participant_cannot_access(self, db: Any, sequence: SharedSequence) -> None:
        # Exercise the access guard directly: rendering Django's 404 page in this
        # environment trips ManifestStaticFilesStorage (no collectstatic), which
        # is orthogonal to the authorization behaviour under test.
        from django.http import Http404

        from suddenly.characters.sequence_views import _get_sequence_for_user

        outsider = User.objects.create_user(username="outsider", email="out@test.com", password="x")

        with pytest.raises(Http404):
            _get_sequence_for_user(str(sequence.pk), outsider)
