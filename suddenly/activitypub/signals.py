"""
Django signals for triggering ActivityPub activities.

These signals automatically federate content when it's created/modified locally.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone


@receiver(post_save, sender='games.Report')
def report_post_save(sender, instance, created, **kwargs):
    """
    When a report is published, broadcast it via ActivityPub.
    """
    from suddenly.activitypub.tasks import send_create_activity
    
    # Only send when status changes to published
    if instance.status == 'published' and instance.published_at:
        # Check if this is a new publication (not just an update)
        # We use a simple heuristic: published_at was just set
        if created or (instance.published_at and 
                       (timezone.now() - instance.published_at).seconds < 10):
            send_create_activity.delay('report', str(instance.id))


@receiver(pre_save, sender='games.Report')
def report_pre_save(sender, instance, **kwargs):
    """
    Set published_at when status changes to published.
    """
    if instance.status == 'published' and not instance.published_at:
        instance.published_at = timezone.now()


@receiver(post_save, sender='characters.Character')
def character_post_save(sender, instance, created, **kwargs):
    """
    When a new character is created locally, broadcast it.
    """
    from suddenly.activitypub.tasks import send_create_activity
    
    if created and not instance.remote:
        send_create_activity.delay('character', str(instance.id))


@receiver(post_save, sender='characters.Quote')
def quote_post_save(sender, instance, created, **kwargs):
    """
    When a public quote is created, broadcast it.
    """
    from suddenly.activitypub.tasks import send_create_activity
    from suddenly.characters.models import QuoteVisibility
    
    if created and not instance.remote and instance.visibility == QuoteVisibility.PUBLIC:
        send_create_activity.delay('quote', str(instance.id))


@receiver(post_save, sender='characters.LinkRequest')
def link_request_post_save(sender, instance, created, **kwargs):
    """
    When a link request is created, send Offer activity.
    When it's accepted/rejected, send corresponding activity.
    """
    from suddenly.activitypub.tasks import (
        send_offer_activity,
        send_accept_activity,
        send_reject_activity,
    )
    from suddenly.characters.models import LinkRequestStatus
    
    if created:
        # New request - send Offer
        send_offer_activity.delay(str(instance.id))
    else:
        # Status change - check if accepted or rejected
        if instance.status == LinkRequestStatus.ACCEPTED:
            send_accept_activity.delay(str(instance.id))
        elif instance.status == LinkRequestStatus.REJECTED:
            send_reject_activity.delay(str(instance.id))


@receiver(post_save, sender='characters.Follow')
def follow_post_save(sender, instance, created, **kwargs):
    """
    When a follow relationship is created, send Follow activity.
    """
    from suddenly.activitypub.tasks import deliver_activity
    from suddenly.activitypub.activities import build_follow_activity
    from suddenly.users.models import User
    from suddenly.games.models import Game
    from suddenly.characters.models import Character, FollowTargetType
    
    if not created:
        return
    
    # Get the target actor
    target = None
    if instance.target_type == FollowTargetType.USER:
        try:
            target = User.objects.get(id=instance.target_id)
        except User.DoesNotExist:
            return
    elif instance.target_type == FollowTargetType.GAME:
        try:
            target = Game.objects.get(id=instance.target_id)
        except Game.DoesNotExist:
            return
    elif instance.target_type == FollowTargetType.CHARACTER:
        try:
            target = Character.objects.get(id=instance.target_id)
        except Character.DoesNotExist:
            return
    
    # Only send if target is remote
    if target and target.remote and hasattr(target, 'inbox_url') and target.inbox_url:
        activity = build_follow_activity(instance.follower, target.actor_url)
        deliver_activity.delay(
            activity=activity,
            inbox_url=target.inbox_url,
            sender_id=str(instance.follower.id),
        )


@receiver(post_save, sender='users.User')
def user_post_save(sender, instance, created, **kwargs):
    """
    Generate ActivityPub keys for new local users.
    """
    from suddenly.activitypub.signatures import generate_key_pair
    
    if created and not instance.remote and not instance.private_key:
        private_key, public_key = generate_key_pair()
        # Use update to avoid triggering signal again
        type(instance).objects.filter(pk=instance.pk).update(
            private_key=private_key,
            public_key=public_key,
        )


@receiver(post_save, sender='games.Game')
def game_post_save(sender, instance, created, **kwargs):
    """
    Generate ActivityPub keys for new local games.
    """
    from suddenly.activitypub.signatures import generate_key_pair
    
    if created and not instance.remote and not instance.private_key:
        private_key, public_key = generate_key_pair()
        type(instance).objects.filter(pk=instance.pk).update(
            private_key=private_key,
            public_key=public_key,
        )
