"""
Domain service for federated direct messages (Epic E, #135, DEC-E5).

``MessageService`` is the single entry point for conversation lifecycle and
message creation. Views, the AP inbox handler, and the outbound-federation
signal all go through it rather than touching the models directly, so the
mutuality gate (DEC-E2) and the canonical pair-ordering rule (DEC-E1) are
enforced in exactly one place.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.utils import timezone


class NotMutualFollowersError(Exception):
    """Raised by :meth:`MessageService.send` when sender and recipient are not
    mutual followers (DEC-E2 — gate applied at send, mirrored at receive)."""


class MessageService:
    """Conversation + DirectMessage lifecycle, local and federated."""

    @staticmethod
    def get_or_create_conversation(user_a: Any, user_b: Any) -> tuple[Any, bool]:
        """Get or create the single :class:`Conversation` for an unordered pair.

        Participants are stored ordered by PK (``participant_low`` <
        ``participant_high``) so the pair always resolves to the same row
        regardless of who initiated it (DEC-E1).
        """
        from .models import Conversation, ConversationMembership

        low, high = sorted([user_a, user_b], key=lambda u: str(u.pk))
        is_remote = bool(getattr(user_a, "remote", False) or getattr(user_b, "remote", False))
        conversation, created = Conversation.objects.get_or_create(
            participant_low=low,
            participant_high=high,
            defaults={"remote": is_remote},
        )
        if created:
            ConversationMembership.objects.bulk_create(
                [
                    ConversationMembership(conversation=conversation, user=low),
                    ConversationMembership(conversation=conversation, user=high),
                ]
            )
        return conversation, created

    @staticmethod
    @transaction.atomic
    def send(sender: Any, recipient: Any, body: str) -> Any:
        """Create and persist a local outbound :class:`DirectMessage`.

        Raises :class:`NotMutualFollowersError` unless the pair mutually
        follows each other (DEC-E2). Federation delivery is triggered by a
        ``post_save`` signal (``activitypub/signals.py``), not from here —
        this service must not depend on ``activitypub``.
        """
        from suddenly.characters.models import Follow

        from .models import DirectMessage

        if not Follow.objects.are_mutual(sender, recipient):
            raise NotMutualFollowersError(f"{sender} and {recipient} are not mutual followers")

        conversation, _ = MessageService.get_or_create_conversation(sender, recipient)
        message = DirectMessage.objects.create(
            conversation=conversation,
            sender=sender,
            body=body,
            remote=False,
        )
        conversation.last_message_at = message.created_at
        conversation.save(update_fields=["last_message_at", "updated_at"])
        return message

    @staticmethod
    def receive_remote(
        conversation: Any, sender: Any, body: str, ap_id: str, published_at: Any = None
    ) -> Any:
        """Persist an inbound federated :class:`DirectMessage`.

        Idempotent by ``ap_id`` — a duplicate delivery is a no-op and returns
        the existing row (DEC-E4). Callers (the AP inbox handler) are
        responsible for the mutuality gate and local-recipient resolution
        before calling this.
        """
        from .models import DirectMessage

        existing = DirectMessage.objects.filter(ap_id=ap_id).first()
        if existing is not None:
            return existing

        message = DirectMessage.objects.create(
            conversation=conversation,
            sender=sender,
            body=body,
            remote=True,
            ap_id=ap_id,
        )
        touched_at = published_at or message.created_at
        if conversation.last_message_at is None or touched_at > conversation.last_message_at:
            conversation.last_message_at = touched_at
            conversation.save(update_fields=["last_message_at", "updated_at"])
        return message

    @staticmethod
    def other_participant(conversation: Any, user: Any) -> Any:
        """Return whichever participant of `conversation` is not `user`."""
        if conversation.participant_low_id == user.pk:
            return conversation.participant_high
        return conversation.participant_low

    @staticmethod
    def mark_read(conversation: Any, user: Any) -> None:
        """Advance `user`'s read cursor on `conversation` to now."""
        from .models import ConversationMembership

        ConversationMembership.objects.filter(conversation=conversation, user=user).update(
            last_read_at=timezone.now()
        )

    @staticmethod
    def unread_for(conversation: Any, user: Any) -> int:
        """Count messages in `conversation` from the other participant, unread by `user`."""
        from .models import ConversationMembership

        membership = ConversationMembership.objects.filter(
            conversation=conversation, user=user
        ).first()
        qs = conversation.messages.exclude(sender=user)
        if membership is not None and membership.last_read_at is not None:
            qs = qs.filter(created_at__gt=membership.last_read_at)
        return int(qs.count())

    @staticmethod
    def unread_count(user: Any) -> int:
        """Total unread direct messages for `user`, across all their conversations."""
        from .models import Conversation

        conversations = Conversation.objects.filter(memberships__user=user).distinct()
        return sum(MessageService.unread_for(c, user) for c in conversations)
