"""
Celery tasks for Suddenly.

Handles:
- ActivityPub delivery
- Quote expiration
- Periodic cleanup
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


# =================================================================
# ActivityPub Delivery Tasks
# =================================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def deliver_activity(self, activity_data: dict, inbox_url: str):
    """
    Deliver an ActivityPub activity to a remote inbox.
    
    Args:
        activity_data: The activity JSON to send
        inbox_url: Target inbox URL
    
    Retries up to 3 times with exponential backoff.
    """
    import httpx
    from suddenly.activitypub.signatures import sign_request
    
    try:
        headers = {
            "Content-Type": "application/activity+json",
            "Accept": "application/activity+json",
        }
        
        # Sign the request
        headers = sign_request(
            method="POST",
            url=inbox_url,
            headers=headers,
            body=activity_data
        )
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                inbox_url,
                json=activity_data,
                headers=headers
            )
            response.raise_for_status()
        
        logger.info(f"Delivered activity to {inbox_url}")
        return {"success": True, "inbox": inbox_url}
        
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP error delivering to {inbox_url}: {e}")
        if e.response.status_code >= 500:
            # Retry on server errors
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        return {"success": False, "error": str(e)}
        
    except Exception as e:
        logger.error(f"Error delivering to {inbox_url}: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task
def broadcast_activity(activity_data: dict, actor_id: str):
    """
    Broadcast an activity to all followers of an actor.
    
    Args:
        activity_data: The activity JSON to send
        actor_id: UUID of the actor (User, Game, or Character)
    """
    from suddenly.characters.models import Follow
    
    # Get all followers (Follow uses GenericFK, so filter on object_id)
    follows = Follow.objects.filter(object_id=actor_id)
    
    for follow in follows:
        if follow.follower.remote and follow.follower.inbox_url:
            deliver_activity.delay(activity_data, follow.follower.inbox_url)
    
    logger.info(f"Queued broadcast to {follows.count()} followers")


@shared_task
def send_create_note(report_id: str):
    """
    Send Create(Note) activity for a published report.
    """
    from suddenly.games.models import Report
    
    try:
        report = Report.objects.select_related("author", "game").get(id=report_id)
    except Report.DoesNotExist:
        logger.error(f"Report {report_id} not found")
        return
    
    if report.status != "published":
        logger.warning(f"Report {report_id} is not published")
        return
    
    activity = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "Create",
        "id": f"{settings.AP_BASE_URL}/activities/{report.id}/create",
        "actor": report.author.actor_url,
        "published": report.published_at.isoformat(),
        "to": ["https://www.w3.org/ns/activitystreams#Public"],
        "cc": [f"{report.author.actor_url}/followers"],
        "object": {
            "type": "Note",
            "id": f"{settings.AP_BASE_URL}/reports/{report.id}",
            "attributedTo": report.author.actor_url,
            "content": report.content[:500],  # Truncate for federation
            "published": report.published_at.isoformat(),
            "url": f"{settings.AP_BASE_URL}/reports/{report.id}",
            "inReplyTo": None,
            "tag": [],  # TODO: Add character mentions as tags
        }
    }
    
    # Broadcast to followers of the game
    broadcast_activity.delay(activity, str(report.game.id))
    
    # Also broadcast to author's followers
    broadcast_activity.delay(activity, str(report.author.id))


@shared_task
def send_offer_activity(link_request_id: str):
    """
    Send Offer activity for a Claim/Adopt/Fork request.
    """
    from suddenly.characters.models import LinkRequest
    
    try:
        request = LinkRequest.objects.select_related(
            "requester", "target_character", "target_character__creator"
        ).get(id=link_request_id)
    except LinkRequest.DoesNotExist:
        logger.error(f"LinkRequest {link_request_id} not found")
        return
    
    activity = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "Offer",
        "id": f"{settings.AP_BASE_URL}/activities/{request.id}/offer",
        "actor": request.requester.actor_url,
        "to": [request.target_character.creator.actor_url],
        "object": {
            "type": request.type.capitalize(),
            "target": request.target_character.actor_url,
            "summary": request.message,
        }
    }
    
    if request.proposed_character:
        activity["object"]["instrument"] = request.proposed_character.actor_url
    
    # Deliver to target character's creator
    if request.target_character.creator.remote:
        deliver_activity.delay(activity, request.target_character.creator.inbox_url)


# =================================================================
# Maintenance Tasks
# =================================================================

@shared_task
def cleanup_expired_quotes():
    """
    Delete ephemeral quotes that have expired.
    
    Should be run periodically (e.g., every hour).
    """
    from suddenly.characters.models import Quote
    
    expired = Quote.objects.filter(
        visibility="ephemeral",
        expires_at__lt=timezone.now()
    )
    
    count = expired.count()
    expired.delete()
    
    logger.info(f"Deleted {count} expired quotes")
    return {"deleted": count}


@shared_task
def cleanup_old_link_requests():
    """
    Clean up old cancelled/rejected link requests.
    
    Keeps requests for 30 days after resolution.
    """
    from suddenly.characters.models import LinkRequest
    
    cutoff = timezone.now() - timedelta(days=30)
    
    old_requests = LinkRequest.objects.filter(
        status__in=["cancelled", "rejected"],
        resolved_at__lt=cutoff
    )
    
    count = old_requests.count()
    old_requests.delete()
    
    logger.info(f"Deleted {count} old link requests")
    return {"deleted": count}


@shared_task
def update_activity_stats():
    """
    Update cached activity statistics.
    
    Can be used for nodeinfo and admin dashboard.
    """
    from django.core.cache import cache
    from suddenly.users.models import User
    from suddenly.games.models import Game, Report
    from suddenly.characters.models import Character
    
    stats = {
        "users_total": User.objects.filter(remote=False, is_active=True).count(),
        "users_active_month": User.objects.filter(
            remote=False,
            is_active=True,
            last_login__gte=timezone.now() - timedelta(days=30)
        ).count(),
        "games_total": Game.objects.filter(remote=False, is_public=True).count(),
        "reports_total": Report.objects.filter(remote=False, status="published").count(),
        "characters_total": Character.objects.filter(remote=False).count(),
        "characters_available": Character.objects.filter(
            remote=False, status="npc"
        ).count(),
        "updated_at": timezone.now().isoformat(),
    }
    
    cache.set("suddenly_stats", stats, timeout=3600)  # Cache for 1 hour
    
    logger.info(f"Updated activity stats: {stats}")
    return stats


# =================================================================
# Periodic Task Registration
# =================================================================

# These are registered in settings.py via CELERY_BEAT_SCHEDULE
# or can be configured in django-celery-beat admin

CELERY_BEAT_SCHEDULE = {
    "cleanup-expired-quotes": {
        "task": "suddenly.core.tasks.cleanup_expired_quotes",
        "schedule": 3600.0,  # Every hour
    },
    "cleanup-old-link-requests": {
        "task": "suddenly.core.tasks.cleanup_old_link_requests",
        "schedule": 86400.0,  # Daily
    },
    "update-activity-stats": {
        "task": "suddenly.core.tasks.update_activity_stats",
        "schedule": 1800.0,  # Every 30 minutes
    },
}
