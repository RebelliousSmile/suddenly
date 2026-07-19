"""
Signals for auto-creating Notifications (US-09, US-20).

Connected in core.apps.CoreConfig.ready().
"""

from __future__ import annotations

import logging
from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender="characters.LinkRequest")
def notify_on_link_request(sender: type, instance: Any, created: bool, **kwargs: Any) -> None:
    """Create notification when a link request is created or resolved."""
    from suddenly.core.models import Notification, NotificationType

    if created:
        # Notify target character's creator
        Notification.objects.create(
            recipient=instance.target_character.creator,
            type=NotificationType.LINK_REQUEST,
            actor=instance.requester,
            message=(
                f"@{instance.requester.username} veut "
                f"{instance.get_type_display().upper()} "
                f"{instance.target_character.name}"
            ),
        )
    else:
        # Status changed — notify requester
        from suddenly.characters.models import LinkRequestStatus

        if instance.status == LinkRequestStatus.ACCEPTED:
            Notification.objects.create(
                recipient=instance.requester,
                type=NotificationType.LINK_ACCEPTED,
                actor=instance.target_character.creator,
                message=(
                    f"@{instance.target_character.creator.username} a accepté votre demande "
                    f"sur {instance.target_character.name}"
                ),
            )
        elif instance.status == LinkRequestStatus.REJECTED:
            Notification.objects.create(
                recipient=instance.requester,
                type=NotificationType.LINK_REJECTED,
                actor=instance.target_character.creator,
                message=(
                    f"@{instance.target_character.creator.username} a refusé votre demande "
                    f"sur {instance.target_character.name}"
                ),
            )


@receiver(post_save, sender="characters.Follow")
def notify_on_follow(sender: type, instance: Any, created: bool, **kwargs: Any) -> None:
    """Create notification when someone follows a user."""
    if not created:
        return

    from django.contrib.contenttypes.models import ContentType

    from suddenly.core.models import Notification, NotificationType
    from suddenly.users.models import User

    user_ct = ContentType.objects.get_for_model(User)
    if instance.content_type_id != user_ct.pk:
        return  # Only notify on user follows

    target = User.objects.filter(pk=instance.object_id).first()
    if not target:
        return

    Notification.objects.create(
        recipient=target,
        type=NotificationType.NEW_FOLLOWER,
        actor=instance.follower,
        message=f"@{instance.follower.username} vous suit",
    )


@receiver(
    post_save,
    sender="core.UserReport",
    dispatch_uid="suddenly.notifications.notify_admins_on_user_report",
)
def notify_admins_on_user_report(sender: type, instance: Any, created: bool, **kwargs: Any) -> None:
    """Notify every local admin when a signalement is filed (#136, DEC-F5).

    Targets exclusively ``is_admin=True, remote=False`` — ``reported_user``
    is never notified (DEC-F6, critère 4: the reported user must not learn
    they were signalé).
    """
    if not created:
        return

    from django.contrib.contenttypes.models import ContentType

    from suddenly.core.models import Notification, NotificationType
    from suddenly.users.models import User

    report_ct = ContentType.objects.get_for_model(instance)
    admins = User.objects.filter(is_admin=True, remote=False).exclude(pk=instance.reported_user_id)
    for admin in admins:
        Notification.objects.create(
            recipient=admin,
            type=NotificationType.MODERATION_REPORT,
            actor=instance.reporter,
            target_content_type=report_ct,
            target_object_id=instance.pk,
            message=(f"@{instance.reporter.username} a signalé @{instance.reported_user.username}"),
        )


@receiver(post_save, sender="games.Report")
def notify_on_report_published(sender: type, instance: Any, created: bool, **kwargs: Any) -> None:
    """Create notifications when a report is published."""
    if instance.status != "published" or not instance.published_at:
        return

    from django.contrib.contenttypes.models import ContentType

    from suddenly.characters.models import Follow
    from suddenly.core.models import Notification, NotificationType
    from suddenly.games.models import Game
    from suddenly.users.models import User

    # Notify followers of the author
    user_ct = ContentType.objects.get_for_model(User)
    author_followers = Follow.objects.filter(
        content_type=user_ct, object_id=instance.author_id
    ).values_list("follower_id", flat=True)

    # Notify followers of the game
    game_ct = ContentType.objects.get_for_model(Game)
    game_followers = Follow.objects.filter(
        content_type=game_ct, object_id=instance.game_id
    ).values_list("follower_id", flat=True)

    follower_ids = set(author_followers) | set(game_followers)
    follower_ids.discard(instance.author_id)  # Don't notify self

    title = instance.title or "Sans titre"
    for fid in follower_ids:
        Notification.objects.create(
            recipient_id=fid,
            type=NotificationType.NEW_REPORT,
            actor=instance.author,
            message=f"@{instance.author.username} a publié « {title} »",
        )

    # Track usage for donation prompts
    _track_usage_and_prompt(instance.author)


def _track_usage_and_prompt(user: Any) -> None:
    """Increment usage stats and create donation prompt if threshold reached."""
    from suddenly.core.models import (
        DonationPrompt,
        InstanceSettings,
        Notification,
        NotificationType,
        UserUsageStats,
    )

    settings_obj = InstanceSettings.get()
    if not settings_obj.donation_enabled:
        return

    stats, _ = UserUsageStats.objects.get_or_create(user=user)
    stats.total_posts += 1
    stats.posts_since_last_prompt += 1
    stats.save(update_fields=["total_posts", "posts_since_last_prompt", "updated_at"])

    if stats.should_prompt(interval=settings_obj.donation_prompt_interval):
        # Create donation prompt
        DonationPrompt.objects.create(
            user=user,
            posts_at_prompt=stats.total_posts,
        )
        stats.posts_since_last_prompt = 0
        stats.save(update_fields=["posts_since_last_prompt", "updated_at"])

        # Notify user
        Notification.objects.create(
            recipient=user,
            type=NotificationType.INVITATION,
            message=(
                f"Vous avez publié {stats.total_posts} comptes-rendus ! "
                f"Suddenly est gratuit et libre. "
                f"Si la plateforme vous est utile, pensez à soutenir l'instance."
            ),
        )


@receiver(post_save, sender="messaging.DirectMessage")
def notify_on_direct_message(sender: type, instance: Any, created: bool, **kwargs: Any) -> None:
    """Notify the other participant when a direct message is created (DEC-E6).

    Fires for both a local outbound send and a mirrored inbound (federated)
    message — both create a local ``DirectMessage`` row, so this single
    signal covers local + federated (DEC-E6's stated intent).
    """
    if not created:
        return

    from suddenly.core.models import Notification, NotificationType
    from suddenly.messaging.services import MessageService

    recipient = MessageService.other_participant(instance.conversation, instance.sender)
    Notification.objects.create(
        recipient=recipient,
        type=NotificationType.DIRECT_MESSAGE,
        actor=instance.sender,
        target=instance.conversation,
        message=f"@{instance.sender.username} vous a envoyé un message",
    )
