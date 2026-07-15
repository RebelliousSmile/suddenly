"""
Tests for ``suddenly.characters.services`` — the LinkService state machine
(Claim / Adopt / Fork) and the character queryset builder.

Covers the audit gap #1 (session 2026-05-17): ``characters/services.py`` held
all of the link-request business logic with no dedicated test. This module
exercises validation, request creation, the PENDING/QUEUED queue, acceptance,
rejection, cancellation, queue promotion + notifications, revocation, and the
check-then-create concurrency invariant (DEC-035).
"""

from __future__ import annotations

import threading
from typing import Any

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import connection

from suddenly.characters.models import (
    Character,
    CharacterLink,
    CharacterLinkStatus,
    CharacterStatus,
    LinkRequest,
    LinkRequestStatus,
    LinkType,
    SharedSequence,
    SharedSequenceStatus,
)
from suddenly.characters.services import LinkService, build_character_queryset
from suddenly.core.models import Notification, NotificationType
from suddenly.games.models import Game
from suddenly.users.models import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pc(owner: User, game: Game, name: str = "Some PC") -> Character:
    """Create a PC owned by ``owner``."""
    return Character.objects.create(
        name=name,
        status=CharacterStatus.PC,
        owner=owner,
        creator=owner,
        origin_game=game,
    )


def _make_pending(
    requester: User, target: Character, link_type: str = LinkType.ADOPT
) -> LinkRequest:
    """Create a raw PENDING request (bypassing the service) for setup."""
    return LinkRequest.objects.create(
        type=link_type,
        requester=requester,
        target_character=target,
        message="setup pending",
        status=LinkRequestStatus.PENDING,
    )


def _make_queued(
    requester: User, target: Character, link_type: str = LinkType.ADOPT
) -> LinkRequest:
    """Create a raw QUEUED request (bypassing the service) for setup."""
    return LinkRequest.objects.create(
        type=link_type,
        requester=requester,
        target_character=target,
        message="setup queued",
        status=LinkRequestStatus.QUEUED,
    )


# ---------------------------------------------------------------------------
# validate_claim / validate_adopt / validate_fork
# ---------------------------------------------------------------------------


class TestValidateClaim:
    def test_target_must_be_npc(self, db: Any, other_user: User, game: Game) -> None:
        target = Character.objects.create(
            name="Already claimed",
            status=CharacterStatus.CLAIMED,
            creator=other_user,
            origin_game=game,
        )
        pc = _make_pc(other_user, game)

        with pytest.raises(ValidationError) as exc:
            LinkService.validate_claim(other_user, target, pc)

        assert "n'est plus disponible" in str(exc.value)

    def test_claim_requires_a_proposed_character(
        self, db: Any, other_user: User, character: Character
    ) -> None:
        with pytest.raises(ValidationError) as exc:
            LinkService.validate_claim(other_user, character, None)

        assert "nécessite un PJ existant" in str(exc.value)

    def test_proposed_character_must_be_pc(
        self, db: Any, other_user: User, character: Character, game: Game
    ) -> None:
        npc = Character.objects.create(
            name="Not a PC", status=CharacterStatus.NPC, creator=other_user, origin_game=game
        )

        with pytest.raises(ValidationError) as exc:
            LinkService.validate_claim(other_user, character, npc)

        assert "n'est pas un PJ" in str(exc.value)

    def test_proposed_character_must_be_owned_by_requester(
        self, db: Any, user: User, other_user: User, character: Character, game: Game
    ) -> None:
        someone_elses_pc = _make_pc(user, game, name="Not mine")

        with pytest.raises(ValidationError) as exc:
            LinkService.validate_claim(other_user, character, someone_elses_pc)

        assert "vos propres PJ" in str(exc.value)

    def test_valid_claim_passes(
        self, db: Any, other_user: User, character: Character, game: Game
    ) -> None:
        pc = _make_pc(other_user, game)
        # Should not raise.
        LinkService.validate_claim(other_user, character, pc)


class TestValidateAdopt:
    def test_target_must_be_npc(self, db: Any, user: User, other_user: User, game: Game) -> None:
        target = _make_pc(user, game, name="Already a PC")

        with pytest.raises(ValidationError) as exc:
            LinkService.validate_adopt(other_user, target)

        assert "n'est plus disponible" in str(exc.value)

    def test_valid_adopt_passes(self, db: Any, other_user: User, character: Character) -> None:
        LinkService.validate_adopt(other_user, character)


class TestValidateFork:
    def test_fork_of_any_status_is_allowed(
        self, db: Any, user: User, other_user: User, game: Game
    ) -> None:
        adopted = Character.objects.create(
            name="Adopted",
            status=CharacterStatus.ADOPTED,
            owner=user,
            creator=user,
            origin_game=game,
        )
        # Neither an NPC nor owned by the requester — still fine.
        LinkService.validate_fork(other_user, adopted)

    def test_missing_target_rejected(self, db: Any, other_user: User) -> None:
        with pytest.raises(ValidationError) as exc:
            LinkService.validate_fork(other_user, None)  # type: ignore[arg-type]

        assert "introuvable" in str(exc.value)


# ---------------------------------------------------------------------------
# create_request
# ---------------------------------------------------------------------------


class TestCreateRequest:
    def test_create_claim_pending(
        self, db: Any, other_user: User, character: Character, game: Game
    ) -> None:
        pc = _make_pc(other_user, game)

        request = LinkService.create_request(
            requester=other_user,
            target_character=character,
            link_type=LinkType.CLAIM,
            message="This was mine",
            proposed_character=pc,
        )

        assert request.type == LinkType.CLAIM
        assert request.status == LinkRequestStatus.PENDING
        assert request.proposed_character == pc

    def test_create_adopt_pending(self, db: Any, other_user: User, character: Character) -> None:
        request = LinkService.create_request(
            requester=other_user,
            target_character=character,
            link_type=LinkType.ADOPT,
            message="Adopt me",
        )
        assert request.type == LinkType.ADOPT
        assert request.status == LinkRequestStatus.PENDING
        assert request.proposed_character is None

    def test_create_fork_pending(self, db: Any, other_user: User, character: Character) -> None:
        request = LinkService.create_request(
            requester=other_user,
            target_character=character,
            link_type=LinkType.FORK,
            message="Fork it",
        )
        assert request.type == LinkType.FORK
        assert request.status == LinkRequestStatus.PENDING

    def test_second_request_is_queued(
        self, db: Any, user: User, other_user: User, character: Character
    ) -> None:
        _make_pending(user, character)

        request = LinkService.create_request(
            requester=other_user,
            target_character=character,
            link_type=LinkType.ADOPT,
            message="I'm second",
        )

        assert request.status == LinkRequestStatus.QUEUED

    def test_unknown_link_type_rejected(
        self, db: Any, other_user: User, character: Character
    ) -> None:
        with pytest.raises(ValidationError) as exc:
            LinkService.create_request(
                requester=other_user,
                target_character=character,
                link_type="teleport",
                message="?",
            )

        assert "Type de lien inconnu" in str(exc.value)

    def test_invalid_claim_does_not_persist_request(
        self, db: Any, other_user: User, character: Character, game: Game
    ) -> None:
        """A failing validation inside the atomic block leaves no row behind."""
        npc = Character.objects.create(
            name="Bad proposed", status=CharacterStatus.NPC, creator=other_user, origin_game=game
        )

        with pytest.raises(ValidationError):
            LinkService.create_request(
                requester=other_user,
                target_character=character,
                link_type=LinkType.CLAIM,
                message="bad",
                proposed_character=npc,
            )

        assert LinkRequest.objects.count() == 0


# ---------------------------------------------------------------------------
# accept_request
# ---------------------------------------------------------------------------


class TestAcceptRequest:
    def test_accept_claim_creates_link_and_sequence(
        self, db: Any, other_user: User, character: Character, game: Game
    ) -> None:
        pc = _make_pc(other_user, game, name="Claimer PC")
        request = LinkRequest.objects.create(
            type=LinkType.CLAIM,
            requester=other_user,
            target_character=character,
            proposed_character=pc,
            message="Claim!",
        )

        link = LinkService.accept_request(request, "Approved!")

        request.refresh_from_db()
        character.refresh_from_db()

        assert request.status == LinkRequestStatus.ACCEPTED
        assert request.response_message == "Approved!"
        assert request.resolved_at is not None
        assert character.status == CharacterStatus.CLAIMED
        assert link.source == pc
        assert link.target == character
        assert link.type == LinkType.CLAIM

        sequence = SharedSequence.objects.get(link=link)
        assert sequence.status == SharedSequenceStatus.DRAFT

    def test_accept_adopt_transfers_ownership(
        self, db: Any, other_user: User, character: Character
    ) -> None:
        request = LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=other_user,
            target_character=character,
            message="Adopt!",
        )

        LinkService.accept_request(request)
        character.refresh_from_db()

        assert character.status == CharacterStatus.ADOPTED
        assert character.owner == other_user

    def test_accept_fork_creates_child_character(
        self, db: Any, other_user: User, character: Character
    ) -> None:
        request = LinkRequest.objects.create(
            type=LinkType.FORK,
            requester=other_user,
            target_character=character,
            message="Fork!",
        )

        before = Character.objects.count()
        link = LinkService.accept_request(request)

        assert Character.objects.count() == before + 1
        assert link.source.parent == character
        assert link.source.owner == other_user
        assert link.source.status == CharacterStatus.PC
        # A fork leaves the original untouched (still an NPC).
        character.refresh_from_db()
        assert character.status == CharacterStatus.NPC

    def test_accept_cancels_remaining_queued_for_claim(
        self, db: Any, user: User, other_user: User, character: Character, game: Game
    ) -> None:
        """Accepting a claim/adopt cancels the other queued requests on the NPC."""
        pc = _make_pc(other_user, game)
        pending = LinkRequest.objects.create(
            type=LinkType.CLAIM,
            requester=other_user,
            target_character=character,
            proposed_character=pc,
            message="Mine",
        )
        queued = _make_queued(user, character)

        LinkService.accept_request(pending)

        queued.refresh_from_db()
        assert queued.status == LinkRequestStatus.CANCELLED
        assert queued.resolved_at is not None

    def test_cannot_accept_non_pending(
        self, db: Any, other_user: User, character: Character
    ) -> None:
        request = LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=other_user,
            target_character=character,
            status=LinkRequestStatus.REJECTED,
            message="already rejected",
        )

        with pytest.raises(ValidationError) as exc:
            LinkService.accept_request(request)

        assert "n'est plus en attente" in str(exc.value)

    def test_accept_unknown_type_rejected(
        self, db: Any, other_user: User, character: Character
    ) -> None:
        request = LinkRequest.objects.create(
            type="teleport",
            requester=other_user,
            target_character=character,
            status=LinkRequestStatus.PENDING,
            message="weird",
        )

        with pytest.raises(ValidationError) as exc:
            LinkService.accept_request(request)

        assert "Type inconnu" in str(exc.value)


# ---------------------------------------------------------------------------
# reject_request + queue promotion (US-15)
# ---------------------------------------------------------------------------


class TestRejectRequest:
    def test_reject_sets_fields(self, db: Any, other_user: User, character: Character) -> None:
        request = _make_pending(other_user, character)

        result = LinkService.reject_request(request, "Not a good fit")

        assert result.status == LinkRequestStatus.REJECTED
        assert result.response_message == "Not a good fit"
        assert result.resolved_at is not None

    def test_reject_promotes_next_queued(
        self, db: Any, user: User, other_user: User, character: Character
    ) -> None:
        """Rejecting the PENDING request promotes the oldest QUEUED one (US-15)."""
        pending = _make_pending(other_user, character)
        queued = _make_queued(user, character)

        LinkService.reject_request(pending)

        queued.refresh_from_db()
        assert queued.status == LinkRequestStatus.PENDING

    def test_reject_promotion_notifies_creator(
        self, db: Any, user: User, other_user: User, character: Character
    ) -> None:
        pending = _make_pending(other_user, character)
        queued = _make_queued(user, character)

        LinkService.reject_request(pending)

        # The promotion notification is the one carrying a target_object_id
        # (the plain "new request" signal notification leaves it null).
        note = Notification.objects.get(
            type=NotificationType.LINK_REQUEST, target_object_id=queued.pk
        )
        assert note.recipient == character.creator
        assert note.actor == queued.requester
        ct = ContentType.objects.get_for_model(LinkRequest)
        assert note.target_content_type == ct

    def test_reject_without_queue_is_noop_on_promotion(
        self, db: Any, other_user: User, character: Character
    ) -> None:
        pending = _make_pending(other_user, character)

        LinkService.reject_request(pending)

        # No queued request to promote → no promotion notification.
        assert not Notification.objects.filter(
            type=NotificationType.LINK_REQUEST, target_object_id__isnull=False
        ).exists()

    def test_cannot_reject_non_pending(
        self, db: Any, other_user: User, character: Character
    ) -> None:
        request = LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=other_user,
            target_character=character,
            status=LinkRequestStatus.ACCEPTED,
            message="already accepted",
        )

        with pytest.raises(ValidationError):
            LinkService.reject_request(request)


# ---------------------------------------------------------------------------
# cancel_request
# ---------------------------------------------------------------------------


class TestCancelRequest:
    def test_cancel_pending_promotes_queued(
        self, db: Any, user: User, other_user: User, character: Character
    ) -> None:
        pending = _make_pending(other_user, character)
        queued = _make_queued(user, character)

        result = LinkService.cancel_request(pending)

        assert result.status == LinkRequestStatus.CANCELLED
        assert result.resolved_at is not None
        queued.refresh_from_db()
        assert queued.status == LinkRequestStatus.PENDING

    def test_cancel_queued_does_not_promote(
        self, db: Any, user: User, other_user: User, character: Character
    ) -> None:
        pending = _make_pending(other_user, character)
        queued = _make_queued(user, character)

        LinkService.cancel_request(queued)

        pending.refresh_from_db()
        queued.refresh_from_db()
        assert queued.status == LinkRequestStatus.CANCELLED
        # The PENDING one is untouched and no promotion notification fired.
        assert pending.status == LinkRequestStatus.PENDING
        assert not Notification.objects.filter(
            type=NotificationType.LINK_REQUEST, target_object_id__isnull=False
        ).exists()

    def test_cannot_cancel_resolved(self, db: Any, other_user: User, character: Character) -> None:
        request = LinkRequest.objects.create(
            type=LinkType.FORK,
            requester=other_user,
            target_character=character,
            status=LinkRequestStatus.ACCEPTED,
            message="done",
        )

        with pytest.raises(ValidationError) as exc:
            LinkService.cancel_request(request)

        assert "n'est plus en attente" in str(exc.value)


# ---------------------------------------------------------------------------
# get_queue_position
# ---------------------------------------------------------------------------


class TestQueuePosition:
    def test_none_for_pending(self, db: Any, other_user: User, character: Character) -> None:
        pending = _make_pending(other_user, character)
        assert LinkService.get_queue_position(pending) is None

    def test_position_is_one_indexed_by_creation_order(
        self, db: Any, user: User, other_user: User, character: Character, game: Game
    ) -> None:
        _make_pending(user, character)
        first = _make_queued(other_user, character)
        third_user = User.objects.create_user(
            username="third", email="third@test.com", password="x"
        )
        second = _make_queued(third_user, character)

        assert LinkService.get_queue_position(first) == 1
        assert LinkService.get_queue_position(second) == 2


# ---------------------------------------------------------------------------
# revoke_link
# ---------------------------------------------------------------------------


class TestRevokeLink:
    def _accepted_adopt_link(self, requester: User, character: Character) -> CharacterLink:
        request = LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=requester,
            target_character=character,
            message="adopt",
        )
        return LinkService.accept_request(request)

    def test_revoke_draft_deletes_link_and_sequence(
        self, db: Any, other_user: User, character: Character
    ) -> None:
        link = self._accepted_adopt_link(other_user, character)
        link_id = link.pk

        LinkService.revoke_link(link, reason="mistake", actor=character.creator)

        assert not CharacterLink.objects.filter(pk=link_id).exists()
        assert not SharedSequence.objects.filter(link_id=link_id).exists()
        character.refresh_from_db()
        assert character.status == CharacterStatus.NPC
        assert character.owner is None

    def test_revoke_published_marks_revoked_and_keeps_sequence(
        self, db: Any, other_user: User, character: Character
    ) -> None:
        link = self._accepted_adopt_link(other_user, character)
        sequence = link.shared_sequence
        sequence.status = SharedSequenceStatus.PUBLISHED
        sequence.save(update_fields=["status"])

        LinkService.revoke_link(link, reason="drift", actor=character.creator)

        link.refresh_from_db()
        assert link.status == CharacterLinkStatus.REVOKED
        assert SharedSequence.objects.filter(pk=sequence.pk).exists()
        character.refresh_from_db()
        assert character.status == CharacterStatus.NPC

    def test_revoke_by_creator_notifies_requester(
        self, db: Any, other_user: User, character: Character
    ) -> None:
        link = self._accepted_adopt_link(other_user, character)

        LinkService.revoke_link(link, reason="x", actor=character.creator)

        note = Notification.objects.get(type=NotificationType.REVOCATION)
        # Creator revoked → the other party (requester) is notified.
        assert note.recipient == other_user
        assert note.actor == character.creator

    def test_revoke_by_requester_notifies_creator(
        self, db: Any, other_user: User, character: Character
    ) -> None:
        link = self._accepted_adopt_link(other_user, character)

        LinkService.revoke_link(link, reason="x", actor=other_user)

        note = Notification.objects.get(type=NotificationType.REVOCATION)
        assert note.recipient == character.creator
        assert note.actor == other_user


# ---------------------------------------------------------------------------
# publish_sequence (Option A: publication finalizes content + notifies parties,
# character status already transitioned at acceptance)
# ---------------------------------------------------------------------------


class TestPublishSequence:
    def _accepted_adopt_sequence(self, requester: User, character: Character) -> SharedSequence:
        request = LinkRequest.objects.create(
            type=LinkType.ADOPT,
            requester=requester,
            target_character=character,
            message="adopt",
        )
        link = LinkService.accept_request(request)
        return link.shared_sequence

    def test_publish_sets_status_published(
        self, db: Any, other_user: User, character: Character
    ) -> None:
        sequence = self._accepted_adopt_sequence(other_user, character)
        assert sequence.status == SharedSequenceStatus.DRAFT

        LinkService.publish_sequence(sequence, actor=character.creator)

        sequence.refresh_from_db()
        assert sequence.status == SharedSequenceStatus.PUBLISHED

    def test_publish_does_not_change_character_status(
        self, db: Any, other_user: User, character: Character
    ) -> None:
        """Option A: status transitioned at acceptance; publication is a no-op on it."""
        sequence = self._accepted_adopt_sequence(other_user, character)
        character.refresh_from_db()
        assert character.status == CharacterStatus.ADOPTED  # set at acceptance

        LinkService.publish_sequence(sequence, actor=character.creator)

        character.refresh_from_db()
        assert character.status == CharacterStatus.ADOPTED  # unchanged

    def test_publish_notifies_other_party(
        self, db: Any, other_user: User, character: Character
    ) -> None:
        sequence = self._accepted_adopt_sequence(other_user, character)

        LinkService.publish_sequence(sequence, actor=character.creator)

        # Publisher (creator) is excluded; the requester is notified.
        note = Notification.objects.get(type=NotificationType.SHARED_SEQUENCE)
        assert note.recipient == other_user
        assert note.actor == character.creator
        ct = ContentType.objects.get_for_model(SharedSequence)
        assert note.target_content_type == ct
        assert note.target_object_id == sequence.pk

    def test_cannot_publish_non_draft(
        self, db: Any, other_user: User, character: Character
    ) -> None:
        sequence = self._accepted_adopt_sequence(other_user, character)
        LinkService.publish_sequence(sequence, actor=character.creator)

        with pytest.raises(ValidationError) as exc:
            LinkService.publish_sequence(sequence, actor=character.creator)

        assert "n'est plus en brouillon" in str(exc.value)


# ---------------------------------------------------------------------------
# Concurrency invariant (DEC-035: atomic check-then-create)
# ---------------------------------------------------------------------------


class TestConcurrencyInvariant:
    def test_two_requests_on_same_npc_yield_one_pending(
        self, db: Any, user: User, other_user: User, character: Character
    ) -> None:
        """Two sequential requests on one NPC leave exactly one PENDING."""
        LinkService.create_request(
            requester=user,
            target_character=character,
            link_type=LinkType.ADOPT,
            message="first",
        )
        LinkService.create_request(
            requester=other_user,
            target_character=character,
            link_type=LinkType.ADOPT,
            message="second",
        )

        statuses = list(
            LinkRequest.objects.filter(target_character=character)
            .order_by("created_at")
            .values_list("status", flat=True)
        )
        assert statuses.count(LinkRequestStatus.PENDING) == 1
        assert statuses.count(LinkRequestStatus.QUEUED) == 1

    @pytest.mark.django_db(transaction=True)
    def test_parallel_requests_serialize_via_row_lock(
        self, transactional_db: Any, django_db_blocker: Any
    ) -> None:
        """
        Two threads racing to create a request on the same NPC must never both
        land on PENDING: ``select_for_update`` on the target character serializes
        the check-then-create (DEC-035).
        """
        owner = User.objects.create_user(username="owner_c", email="oc@test.com", password="x")
        game = Game.objects.create(title="Race Game", game_system="S", owner=owner)
        npc = Character.objects.create(
            name="Contested", status=CharacterStatus.NPC, creator=owner, origin_game=game
        )
        u1 = User.objects.create_user(username="racer1", email="r1@test.com", password="x")
        u2 = User.objects.create_user(username="racer2", email="r2@test.com", password="x")

        barrier = threading.Barrier(2)
        errors: list[Exception] = []

        def worker(requester: User) -> None:
            try:
                barrier.wait(timeout=5)
                LinkService.create_request(
                    requester=requester,
                    target_character=npc,
                    link_type=LinkType.ADOPT,
                    message=f"race {requester.username}",
                )
            except Exception as exc:  # pragma: no cover - surfaced via errors list
                errors.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker, args=(u,)) for u in (u1, u2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, errors
        statuses = list(
            LinkRequest.objects.filter(target_character=npc).values_list("status", flat=True)
        )
        assert statuses.count(LinkRequestStatus.PENDING) == 1
        assert statuses.count(LinkRequestStatus.QUEUED) == 1


# ---------------------------------------------------------------------------
# build_character_queryset
# ---------------------------------------------------------------------------


class TestBuildCharacterQueryset:
    def test_filters_by_status(self, db: Any, user: User, game: Game) -> None:
        Character.objects.create(
            name="An NPC", status=CharacterStatus.NPC, creator=user, origin_game=game
        )
        _make_pc(user, game, name="A PC")

        npcs = build_character_queryset(status=CharacterStatus.NPC)
        assert all(c.status == CharacterStatus.NPC for c in npcs)
        assert npcs.count() == 1

    def test_invalid_status_is_ignored(self, db: Any, user: User, game: Game) -> None:
        Character.objects.create(
            name="X", status=CharacterStatus.NPC, creator=user, origin_game=game
        )
        # A bogus status value must not filter anything out.
        assert build_character_queryset(status="not-a-status").count() == 1

    def test_no_system_filter_param(self, db: Any, user: User) -> None:
        """US-07: character discovery is by name + tags, not game system.

        The ``system`` filter was removed with the FoundryVTT catalogue —
        build_character_queryset no longer accepts it.
        """
        import pytest

        with pytest.raises(TypeError):
            build_character_queryset(system="cthulhu")  # type: ignore[call-arg]

    def test_filters_by_tag(self, db: Any, user: User, game: Game) -> None:
        from suddenly.core.models import Tag

        tag = Tag.objects.create(name="hero")
        tagged = Character.objects.create(
            name="Tagged", status=CharacterStatus.NPC, creator=user, origin_game=game
        )
        tagged.tags.add(tag)
        Character.objects.create(
            name="Untagged", status=CharacterStatus.NPC, creator=user, origin_game=game
        )

        result = build_character_queryset(tag="hero")
        assert [c.name for c in result] == ["Tagged"]

    def test_full_text_search(self, db: Any, user: User, game: Game) -> None:
        Character.objects.create(
            name="Aragorn",
            description="ranger of the north",
            status=CharacterStatus.NPC,
            creator=user,
            origin_game=game,
        )
        Character.objects.create(
            name="Legolas",
            description="elf archer",
            status=CharacterStatus.NPC,
            creator=user,
            origin_game=game,
        )

        result = build_character_queryset(q="Aragorn")
        assert [c.name for c in result] == ["Aragorn"]

    def test_excludes_remote_characters(self, db: Any, user: User, game: Game) -> None:
        Character.objects.create(
            name="Local", status=CharacterStatus.NPC, creator=user, origin_game=game
        )
        Character.objects.create(
            name="Remote",
            status=CharacterStatus.NPC,
            creator=user,
            origin_game=game,
            remote=True,
            ap_id="https://example.test/characters/remote",
        )

        names = [c.name for c in build_character_queryset()]
        assert "Local" in names
        assert "Remote" not in names
