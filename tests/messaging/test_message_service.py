"""Tests for MessageService — federated direct messages (Epic E, #135).

Covers the DEC-E invariants: canonical pair ordering + idempotent conversation
(E1), the mutual-follow send gate (E2), idempotent remote receive by ap_id (E4),
and the unread read-cursor logic.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.contenttypes.models import ContentType

from suddenly.characters.models import Follow
from suddenly.messaging.models import Conversation, DirectMessage
from suddenly.messaging.services import MessageService, NotMutualFollowersError
from suddenly.users.models import User
from tests.factories import UserFactory


def _follow(follower: User, target: User) -> None:
    """Create an accepted User→User follow."""
    Follow.objects.create(
        follower=follower,
        content_type=ContentType.objects.get_for_model(User),
        object_id=target.pk,
        accepted=True,
    )


def _make_mutual(a: User, b: User) -> None:
    _follow(a, b)
    _follow(b, a)


@pytest.fixture
def alice(db: Any) -> User:
    return UserFactory(username="alice", email="alice@example.com")  # type: ignore[return-value,no-untyped-call]


@pytest.fixture
def bob(db: Any) -> User:
    return UserFactory(username="bob", email="bob@example.com")  # type: ignore[return-value,no-untyped-call]


@pytest.mark.django_db
class TestConversation:
    def test_pair_is_canonical_and_idempotent(self, alice: User, bob: User) -> None:
        conv1, created1 = MessageService.get_or_create_conversation(alice, bob)
        conv2, created2 = MessageService.get_or_create_conversation(bob, alice)
        assert created1 is True
        assert created2 is False
        assert conv1.pk == conv2.pk
        assert Conversation.objects.count() == 1

    def test_other_participant(self, alice: User, bob: User) -> None:
        conv, _ = MessageService.get_or_create_conversation(alice, bob)
        assert MessageService.other_participant(conv, alice) == bob
        assert MessageService.other_participant(conv, bob) == alice


@pytest.mark.django_db
class TestSendGate:
    def test_send_requires_mutual_follow(self, alice: User, bob: User) -> None:
        with pytest.raises(NotMutualFollowersError):
            MessageService.send(alice, bob, "salut")
        # one-directional is still not mutual
        _follow(alice, bob)
        with pytest.raises(NotMutualFollowersError):
            MessageService.send(alice, bob, "salut")
        assert DirectMessage.objects.count() == 0

    def test_send_succeeds_when_mutual(self, alice: User, bob: User) -> None:
        _make_mutual(alice, bob)
        msg = MessageService.send(alice, bob, "salut")
        assert msg.body == "salut"
        assert msg.sender == alice
        assert msg.remote is False
        msg.conversation.refresh_from_db()
        assert msg.conversation.last_message_at is not None


@pytest.mark.django_db
class TestReceiveRemote:
    def test_receive_is_idempotent_by_ap_id(self, alice: User, bob: User) -> None:
        conv, _ = MessageService.get_or_create_conversation(alice, bob)
        ap_id = "https://remote.example/messages/1"
        m1 = MessageService.receive_remote(conv, bob, "coucou", ap_id=ap_id)
        m2 = MessageService.receive_remote(conv, bob, "coucou", ap_id=ap_id)
        assert m1.pk == m2.pk
        assert DirectMessage.objects.filter(ap_id=ap_id).count() == 1


@pytest.mark.django_db
class TestUnread:
    def test_unread_then_mark_read(self, alice: User, bob: User) -> None:
        _make_mutual(alice, bob)
        MessageService.send(bob, alice, "un")
        MessageService.send(bob, alice, "deux")
        conv, _ = MessageService.get_or_create_conversation(alice, bob)
        # Alice has two unread from bob; bob has none from alice.
        assert MessageService.unread_for(conv, alice) == 2
        assert MessageService.unread_for(conv, bob) == 0
        MessageService.mark_read(conv, alice)
        assert MessageService.unread_for(conv, alice) == 0
        assert MessageService.unread_count(alice) == 0
