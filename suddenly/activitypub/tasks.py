"""
Celery tasks for ActivityPub federation.
"""

import json
import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


# =================================================================
# Incoming activities processing
# =================================================================

@shared_task(bind=True, max_retries=3)
def process_incoming_activity(self, user_id, activity, game_id=None, character_id=None):
    """
    Process an incoming ActivityPub activity.
    """
    try:
        activity_type = activity.get("type")
        
        handlers = {
            "Follow": handle_follow,
            "Undo": handle_undo,
            "Create": handle_create,
            "Update": handle_update,
            "Delete": handle_delete,
            "Accept": handle_accept,
            "Reject": handle_reject,
            "Offer": handle_offer,
        }
        
        handler = handlers.get(activity_type)
        if handler:
            handler(activity, user_id, game_id, character_id)
        else:
            logger.warning(f"Unknown activity type: {activity_type}")
            
    except Exception as e:
        logger.exception(f"Error processing activity: {e}")
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))


def handle_follow(activity, user_id, game_id, character_id):
    """Handle incoming Follow activity."""
    from suddenly.users.models import User
    from suddenly.games.models import Game
    from suddenly.characters.models import Character, Follow
    from django.contrib.contenttypes.models import ContentType
    
    actor_url = activity.get("actor")
    follower = get_or_create_remote_user(actor_url)
    if not follower:
        return
    
    target = None
    content_type = None
    
    if user_id:
        target = User.objects.filter(id=user_id).first()
        content_type = ContentType.objects.get_for_model(User)
    elif game_id:
        target = Game.objects.filter(id=game_id).first()
        content_type = ContentType.objects.get_for_model(Game)
    elif character_id:
        target = Character.objects.filter(id=character_id).first()
        content_type = ContentType.objects.get_for_model(Character)
    
    if not target:
        return
    
    Follow.objects.get_or_create(
        follower=follower,
        content_type=content_type,
        object_id=target.id,
        defaults={"remote": True, "ap_id": activity.get("id")}
    )
    
    send_accept_follow.delay(str(target.id), type(target).__name__, activity)


def handle_undo(activity, user_id, game_id, character_id):
    """Handle Undo activity."""
    obj = activity.get("object", {})
    if obj.get("type") == "Follow":
        from suddenly.characters.models import Follow
        Follow.objects.filter(ap_id=obj.get("id")).delete()


def handle_create(activity, user_id, game_id, character_id):
    logger.info(f"Received Create: {activity.get('object', {}).get('type')}")


def handle_update(activity, user_id, game_id, character_id):
    logger.info("Received Update")


def handle_delete(activity, user_id, game_id, character_id):
    logger.info("Received Delete")


def handle_accept(activity, user_id, game_id, character_id):
    logger.info("Received Accept")


def handle_reject(activity, user_id, game_id, character_id):
    logger.info("Received Reject")


def handle_offer(activity, user_id, game_id, character_id):
    """Handle Offer (link requests from remote)."""
    logger.info("Received Offer")


# =================================================================
# Outgoing activities
# =================================================================

@shared_task(bind=True, max_retries=3)
def deliver_activity(self, activity, inbox_url):
    """Deliver an activity to a remote inbox."""
    import httpx
    
    try:
        headers = {
            "Content-Type": "application/activity+json",
            "Accept": "application/activity+json",
        }
        
        with httpx.Client(timeout=30) as client:
            response = client.post(inbox_url, json=activity, headers=headers)
            
        if response.status_code >= 500:
            raise self.retry(countdown=60 * (self.request.retries + 1))
            
    except httpx.RequestError as e:
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))


@shared_task
def broadcast_activity(activity, actor_id, actor_type):
    """Broadcast an activity to all followers."""
    from suddenly.characters.models import Follow
    from django.contrib.contenttypes.models import ContentType
    
    model_map = {
        "User": ("users", "user"),
        "Game": ("games", "game"), 
        "Character": ("characters", "character"),
    }
    
    app_label, model_name = model_map.get(actor_type, (None, None))
    if not app_label:
        return
        
    content_type = ContentType.objects.get(app_label=app_label, model=model_name)
    
    followers = Follow.objects.filter(
        content_type=content_type,
        object_id=actor_id
    ).select_related("follower")
    
    inboxes = {f.follower.inbox_url for f in followers if f.follower.inbox_url}
    
    for inbox_url in inboxes:
        deliver_activity.delay(activity, inbox_url)


@shared_task
def send_accept_follow(target_id, target_type, follow_activity):
    """Send Accept for a follow request."""
    from suddenly.users.models import User
    from suddenly.games.models import Game
    from suddenly.characters.models import Character
    from .serializers import create_accept_activity
    
    models = {"User": User, "Game": Game, "Character": Character}
    Model = models.get(target_type)
    if not Model:
        return
    
    target = Model.objects.filter(id=target_id).first()
    if not target:
        return
    
    accept = create_accept_activity(target, follow_activity)
    
    actor_url = follow_activity.get("actor")
    remote_user = User.objects.filter(ap_id=actor_url).first()
    if remote_user and remote_user.inbox_url:
        deliver_activity.delay(accept, remote_user.inbox_url)


@shared_task
def send_create_activity(object_type, object_id):
    """
    Send a Create activity for new content.
    
    Args:
        object_type: 'report', 'character', or 'quote'
        object_id: UUID of the object
    """
    from suddenly.games.models import Report
    from suddenly.characters.models import Character, Quote
    from .serializers import (
        serialize_report,
        serialize_character,
        serialize_quote,
        create_create_activity,
    )
    
    if object_type == "report":
        obj = Report.objects.filter(id=object_id).select_related("author", "game").first()
        if not obj or obj.remote:
            return
        serialized = serialize_report(obj)
        actor = obj.game  # Game is the actor for reports
        actor_type = "Game"
    
    elif object_type == "character":
        obj = Character.objects.filter(id=object_id).select_related("origin_game").first()
        if not obj or obj.remote:
            return
        serialized = serialize_character(obj)
        actor = obj.origin_game
        actor_type = "Game"
    
    elif object_type == "quote":
        obj = Quote.objects.filter(id=object_id).select_related("character").first()
        if not obj or obj.remote:
            return
        serialized = serialize_quote(obj)
        actor = obj.character
        actor_type = "Character"
    
    else:
        return
    
    activity = create_create_activity(actor, serialized)
    broadcast_activity.delay(activity, str(actor.id), actor_type)


@shared_task
def send_offer_activity(link_request_id):
    """Send Offer activity for a link request."""
    from suddenly.characters.models import LinkRequest
    from .serializers import serialize_link_request
    
    request = LinkRequest.objects.filter(id=link_request_id).select_related(
        "requester", "target_character", "target_character__creator"
    ).first()
    
    if not request:
        return
    
    activity = serialize_link_request(request)
    
    # Send to target character's creator
    creator = request.target_character.creator
    if creator and creator.remote and creator.inbox_url:
        deliver_activity.delay(activity, creator.inbox_url)


@shared_task
def send_accept_activity(link_request_id):
    """Send Accept activity for an accepted link request."""
    from suddenly.characters.models import LinkRequest
    from .serializers import serialize_link_request, create_accept_activity
    
    request = LinkRequest.objects.filter(id=link_request_id).select_related(
        "requester", "target_character", "target_character__creator"
    ).first()
    
    if not request:
        return
    
    offer = serialize_link_request(request)
    creator = request.target_character.creator
    accept = create_accept_activity(creator, offer)
    
    # Send to requester
    if request.requester.remote and request.requester.inbox_url:
        deliver_activity.delay(accept, request.requester.inbox_url)


@shared_task
def send_reject_activity(link_request_id):
    """Send Reject activity for a rejected link request."""
    from suddenly.characters.models import LinkRequest
    from .serializers import serialize_link_request, create_reject_activity
    
    request = LinkRequest.objects.filter(id=link_request_id).select_related(
        "requester", "target_character", "target_character__creator"
    ).first()
    
    if not request:
        return
    
    offer = serialize_link_request(request)
    creator = request.target_character.creator
    reject = create_reject_activity(creator, offer)
    
    # Send to requester
    if request.requester.remote and request.requester.inbox_url:
        deliver_activity.delay(reject, request.requester.inbox_url)


# =================================================================
# Periodic tasks
# =================================================================

@shared_task
def cleanup_expired_quotes():
    """Delete expired ephemeral quotes."""
    from suddenly.characters.models import Quote, QuoteVisibility
    
    Quote.objects.filter(
        visibility=QuoteVisibility.EPHEMERAL,
        expires_at__lt=timezone.now()
    ).delete()


@shared_task
def refresh_remote_actors():
    """Refresh stale remote actors."""
    from suddenly.users.models import User
    
    stale = User.objects.filter(
        remote=True,
        updated_at__lt=timezone.now() - timedelta(hours=24)
    )[:100]
    
    for user in stale:
        fetch_remote_actor.delay(user.ap_id)


@shared_task
def fetch_remote_actor(actor_url):
    """Fetch and update a remote actor."""
    import httpx
    
    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(
                actor_url,
                headers={"Accept": "application/activity+json"}
            )
            
        if response.status_code == 200:
            update_remote_user(actor_url, response.json())
    except Exception as e:
        logger.exception(f"Error fetching {actor_url}: {e}")


# =================================================================
# Helpers
# =================================================================

def get_or_create_remote_user(actor_url):
    """Get or create a remote user."""
    from suddenly.users.models import User
    import httpx
    
    user = User.objects.filter(ap_id=actor_url).first()
    if user:
        return user
    
    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(
                actor_url,
                headers={"Accept": "application/activity+json"}
            )
            
        if response.status_code != 200:
            return None
            
        data = response.json()
        
        from urllib.parse import urlparse
        domain = urlparse(actor_url).netloc
        username = data.get("preferredUsername", "unknown")
        
        return User.objects.create(
            username=f"{username}@{domain}"[:150],
            remote=True,
            ap_id=actor_url,
            inbox_url=data.get("inbox"),
            outbox_url=data.get("outbox"),
            display_name=data.get("name", username)[:100],
            bio=data.get("summary", ""),
            public_key=data.get("publicKey", {}).get("publicKeyPem", ""),
        )
    except Exception as e:
        logger.exception(f"Error creating remote user: {e}")
        return None


def update_remote_user(actor_url, data):
    """Update remote user from AP data."""
    from suddenly.users.models import User
    
    User.objects.filter(ap_id=actor_url).update(
        inbox_url=data.get("inbox"),
        outbox_url=data.get("outbox"),
        display_name=data.get("name", "")[:100],
        bio=data.get("summary", ""),
        public_key=data.get("publicKey", {}).get("publicKeyPem", ""),
        updated_at=timezone.now(),
    )
