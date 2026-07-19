"""Central moderation service (#136, DEC-F3).

Single point of truth for the instance-interaction ban (the "blocked" state,
distinct from `User.is_active` login suspension — US-25 — and from the
peer-to-peer `UserBlock` — US-33) and for filing signalements against a
user.

Consumed NOW by the two Follow seams that exist in this worktree:
`characters.follow_views.follow_toggle` (local) and
`activitypub.inbox.handle_follow` (inbound federated).

Epic E (#135, direct messages) and epic B (#132, Offers) are NOT merged in
this worktree. When they land, their message-send and offer-response entry
points call `is_blocked(sender)` / `is_blocked(recipient)` the same way this
module documents. No code for those modules is added here — DEC-F3
isolation: this service has no import on, and no coupling to, MP or Offers
code.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.db import transaction
from django.utils import timezone

from suddenly.core.models import UserReport, UserReportStatus

if TYPE_CHECKING:
    from django.db.models import Model

    from suddenly.users.models import User


def is_blocked(user: Any) -> bool:
    """True if `user` is banned from interacting with the instance (#136).

    Tolerant to any object exposing an `is_blocked` attribute (a remote
    `User` mirror always does), so this is safe to call on federation-side
    actors resolved via `get_or_create_remote_user`, and is the single seam
    every interaction surface (Follow now; MP/Offers once merged) must call
    before creating a Follow, sending a message, or accepting an Offer.
    """
    return bool(getattr(user, "is_blocked", False))


@transaction.atomic
def block_user(user: User, *, by: User, report: UserReport | None = None) -> None:
    """Ban `user` from interacting with the instance. Idempotent.

    If `report` is given, also marks it resolved — this is how the admin
    "Bloquer" action in the moderation queue both bans the user and closes
    the triggering signalement in a single call (DEC-F4).
    """
    now = timezone.now()
    if not user.is_blocked:
        user.is_blocked = True
        user.blocked_at = now
        user.blocked_by_admin = by
        user.save(update_fields=["is_blocked", "blocked_at", "blocked_by_admin", "updated_at"])

    if report is not None and report.status != UserReportStatus.RESOLVED:
        report.status = UserReportStatus.RESOLVED
        report.handled_by = by
        report.handled_at = now
        report.save(update_fields=["status", "handled_by", "handled_at", "updated_at"])


def unblock_user(user: User) -> None:
    """Lift the instance-interaction ban on `user`. Idempotent, resets audit."""
    if not user.is_blocked:
        return
    user.is_blocked = False
    user.blocked_at = None
    user.blocked_by_admin = None
    user.save(update_fields=["is_blocked", "blocked_at", "blocked_by_admin", "updated_at"])


def create_user_report(
    reporter: User,
    reported_user: User,
    category: str,
    comment: str = "",
    context: Model | None = None,
) -> UserReport:
    """File a signalement of `reported_user` by `reporter` (#136, DEC-F1).

    `context` is an optional model instance (a scene, a character, or — once
    epic E lands — a direct message) recorded via `GenericForeignKey`. Per
    the GFK-in-`.create()` pitfall, the underlying `context_content_type` /
    `context_object_id` fields are set explicitly rather than passing
    `context=` to the manager (which Django would silently ignore).

    Raises `ValueError` on self-report — a user cannot report themselves.
    Does not notify `reported_user` (DEC-F6, critère 4): the post_save
    signal in `core.notification_signals` targets admins exclusively.
    """
    if reporter.pk == reported_user.pk:
        raise ValueError("A user cannot report themselves")

    kwargs: dict[str, Any] = {
        "reporter": reporter,
        "reported_user": reported_user,
        "category": category,
        "comment": comment,
    }
    if context is not None:
        from django.contrib.contenttypes.models import ContentType

        kwargs["context_content_type"] = ContentType.objects.get_for_model(context)
        kwargs["context_object_id"] = context.pk

    return UserReport.objects.create(**kwargs)
