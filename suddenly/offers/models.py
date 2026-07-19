"""
Social Offer models — collective-intelligence replacement for Muses (Epic B, #132).

A ``SocialOffer`` is addressed to the emitter's followers by one of the three
seams left degrading cleanly by Epic A: scene import summary, link-request
analysis, sequence opening. Followers answer with ``OfferResponse``; the
emitter accepts one (materializing a literal ``Rapport`` post, see DEC-B4)
or declines.

No business logic here (rule: models carry no behavior) — see
``offers/services.py`` for ``OfferService``.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from suddenly.core.models import BaseModel


class OfferKind(models.TextChoices):
    """Which of the 3 degrading seams this Offer re-branches (DEC-B2)."""

    SUMMARY = "summary", "Résumé d'import de scène"
    LINK_ANALYSIS = "link_analysis", "Analyse de lien"
    SEQUENCE_OPENING = "sequence_opening", "Ouverture de séquence"


class OfferStatus(models.TextChoices):
    """SocialOffer lifecycle (DEC-B3 drives the open -> expired transition)."""

    OPEN = "open", "Ouverte"
    RESOLVED = "resolved", "Résolue"
    EXPIRED = "expired", "Expirée"
    CANCELLED = "cancelled", "Annulée"


class OfferResponseStatus(models.TextChoices):
    """A single follower's answer to a SocialOffer."""

    PENDING = "pending", "En attente"
    ACCEPTED = "accepted", "Acceptée"
    DECLINED = "declined", "Déclinée"


class SocialOffer(BaseModel):
    """
    An Offer addressed to the emitter's followers on one of the 3 seams.

    ``target`` (GFK) is the carrier object: a ``games.Report`` (summary),
    a ``characters.LinkRequest`` (link_analysis), or a
    ``characters.SharedSequence`` (sequence_opening) — DEC-B2.
    """

    emitter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_offers",
    )
    kind = models.CharField(max_length=20, choices=OfferKind.choices)

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={"model__in": ("report", "linkrequest", "sharedsequence")},
    )
    object_id = models.UUIDField()
    target = GenericForeignKey("content_type", "object_id")

    status = models.CharField(max_length=10, choices=OfferStatus.choices, default=OfferStatus.OPEN)

    # ActivityPub
    remote = models.BooleanField(default=False)
    ap_id = models.URLField(max_length=500, blank=True, null=True, unique=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["emitter", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.kind} offer by {self.emitter} ({self.status})"


class OfferResponse(BaseModel):
    """
    A follower's answer to a ``SocialOffer``.

    Accepting one response (``OfferService.accept_response``) materializes a
    literal ``Rapport`` (Post) — tracked here via ``created_post`` for
    idempotence and seam-to-UI linkage (DEC-B4).
    """

    offer = models.ForeignKey(
        SocialOffer,
        on_delete=models.CASCADE,
        related_name="responses",
    )
    responder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="offer_responses",
    )
    content = models.TextField()
    status = models.CharField(
        max_length=10,
        choices=OfferResponseStatus.choices,
        default=OfferResponseStatus.PENDING,
    )

    # ActivityPub
    remote = models.BooleanField(default=False)
    ap_id = models.URLField(max_length=500, blank=True, null=True, unique=True)

    # The literal Post materialized when this response is accepted (DEC-B4).
    created_post = models.ForeignKey(
        "games.Rapport",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["created_at"]
        unique_together = ["offer", "responder"]

    def __str__(self) -> str:
        return f"{self.responder} -> {self.offer} ({self.status})"
