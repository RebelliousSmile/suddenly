"""
Federated direct message models for Suddenly (Epic E, #135).

One :class:`Conversation` per mutual-follow pair (canonical ordering by PK —
see :func:`suddenly.messaging.services.MessageService.get_or_create_conversation`
for the ordering logic; models carry no business logic per project convention).
:class:`ConversationMembership` tracks each participant's read cursor.
:class:`DirectMessage` is the actual message, local or federated (mirrored via
``ap_id``, per DEC-E4's idempotent inbox handling).
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from suddenly.core.models import BaseModel


class Conversation(BaseModel):
    """A 1:1 direct-message thread between two mutually-following users.

    ``participant_low``/``participant_high`` are ordered by PK (see
    ``MessageService.get_or_create_conversation``) so the pair is always
    addressed the same way regardless of who initiated it — this is what makes
    ``unique_together`` a real "one conversation per pair" guarantee.
    """

    participant_low = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    participant_high = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    remote = models.BooleanField(
        default=False, help_text="True if either participant is a remote actor"
    )

    class Meta:
        unique_together = ["participant_low", "participant_high"]
        ordering = ["-last_message_at"]

    def __str__(self) -> str:
        return f"Conversation({self.participant_low_id}, {self.participant_high_id})"


class ConversationMembership(BaseModel):
    """A participant's membership in a :class:`Conversation`, with its read cursor."""

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ["conversation", "user"]

    def __str__(self) -> str:
        return f"{self.user} in {self.conversation}"


class DirectMessage(BaseModel):
    """A single message within a :class:`Conversation`.

    ``ap_id`` is set only for federated (received) messages — it is the
    idempotence key for inbound ``Create(Note)`` Direct activities (DEC-E4).
    """

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    body = models.TextField()
    remote = models.BooleanField(default=False, help_text="True if received via federation")
    ap_id = models.URLField(blank=True, null=True, unique=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.sender} in {self.conversation}: {self.body[:30]}"
