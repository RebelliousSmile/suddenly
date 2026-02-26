"""
ActivityPub inbox views for receiving federated activities.
"""

import json
import logging

from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .signatures import verify_signature

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def user_inbox(request, username):
    """
    Inbox endpoint for receiving activities addressed to a user.
    
    POST /users/{username}/inbox
    """
    return process_inbox(request, actor_type='user', actor_identifier=username)


@csrf_exempt
@require_POST
def game_inbox(request, game_id):
    """
    Inbox endpoint for receiving activities addressed to a game.
    
    POST /games/{id}/inbox
    """
    return process_inbox(request, actor_type='game', actor_identifier=game_id)


@csrf_exempt
@require_POST
def character_inbox(request, character_id):
    """
    Inbox endpoint for receiving activities addressed to a character.
    
    POST /characters/{id}/inbox
    """
    return process_inbox(request, actor_type='character', actor_identifier=character_id)


def process_inbox(request, actor_type: str, actor_identifier: str):
    """
    Common inbox processing logic.
    """
    # Verify HTTP signature
    is_valid, reason = verify_signature(request)
    if not is_valid:
        logger.warning(f"Invalid signature for {actor_type} inbox: {actor_identifier} — {reason}")
        return HttpResponse("Invalid signature", status=401)
    
    # Parse activity
    try:
        activity = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")
    
    activity_type = activity.get('type')
    
    if not activity_type:
        return HttpResponseBadRequest("Missing activity type")
    
    logger.info(f"Received {activity_type} for {actor_type}/{actor_identifier}")
    
    # Route to appropriate handler
    handlers = {
        'Follow': handle_follow,
        'Undo': handle_undo,
        'Create': handle_create,
        'Update': handle_update,
        'Delete': handle_delete,
        'Offer': handle_offer,
        'Accept': handle_accept,
        'Reject': handle_reject,
    }
    
    handler = handlers.get(activity_type)
    if handler:
        try:
            handler(activity, actor_type, actor_identifier)
        except Exception as e:
            logger.error(f"Error handling {activity_type}: {e}")
            # Still return 202 - we received it, processing failed
    else:
        logger.warning(f"Unknown activity type: {activity_type}")
    
    # ActivityPub spec says to return 202 Accepted
    return HttpResponse(status=202)


def handle_follow(activity: dict, actor_type: str, actor_identifier: str):
    """
    Handle incoming Follow activity.
    
    Create a Follow record and optionally auto-accept.
    """
    from suddenly.users.models import User
    from suddenly.characters.models import Follow, FollowTargetType
    
    follower_id = activity.get('actor')
    if not follower_id:
        return
    
    # Get or create the remote follower
    follower, _ = get_or_create_remote_user(follower_id)
    if not follower:
        return
    
    # Determine target
    target_type = {
        'user': FollowTargetType.USER,
        'game': FollowTargetType.GAME,
        'character': FollowTargetType.CHARACTER,
    }.get(actor_type)
    
    if not target_type:
        return
    
    # Get target ID
    target = get_local_actor(actor_type, actor_identifier)
    if not target:
        return
    
    # Create follow relationship
    Follow.objects.get_or_create(
        follower=follower,
        target_type=target_type,
        target_id=target.id,
    )
    
    # Send Accept activity
    from .tasks import deliver_activity
    from .activities import get_context
    
    accept_activity = {
        "@context": get_context(),
        "type": "Accept",
        "actor": target.actor_url,
        "object": activity,
    }
    
    deliver_activity.delay(
        activity=accept_activity,
        inbox_url=follower.inbox_url,
        sender_id=str(target.id),
    )


def handle_undo(activity: dict, actor_type: str, actor_identifier: str):
    """
    Handle Undo activity (e.g., unfollow).
    """
    from suddenly.characters.models import Follow
    
    inner = activity.get('object', {})
    inner_type = inner.get('type') if isinstance(inner, dict) else None
    
    if inner_type == 'Follow':
        # Undo follow = unfollow
        follower_id = activity.get('actor')
        follower = get_remote_user(follower_id)
        if follower:
            target = get_local_actor(actor_type, actor_identifier)
            if target:
                Follow.objects.filter(
                    follower=follower,
                    target_id=target.id,
                ).delete()


def handle_create(activity: dict, actor_type: str, actor_identifier: str):
    """
    Handle incoming Create activity.
    
    Could be a remote report, quote, or character.
    """
    obj = activity.get('object', {})
    obj_type = obj.get('type')
    
    if obj_type == 'Note':
        # Could be a report or quote - store for display
        # Implementation depends on how you want to handle remote content
        logger.info(f"Received remote Note: {obj.get('id')}")
    
    # For now, just log it
    logger.info(f"Received Create({obj_type}) from {activity.get('actor')}")


def handle_update(activity: dict, actor_type: str, actor_identifier: str):
    """
    Handle Update activity.
    """
    logger.info(f"Received Update from {activity.get('actor')}")


def handle_delete(activity: dict, actor_type: str, actor_identifier: str):
    """
    Handle Delete activity.
    """
    logger.info(f"Received Delete from {activity.get('actor')}")


def handle_offer(activity: dict, actor_type: str, actor_identifier: str):
    """
    Handle Offer activity (claim/adopt/fork request from remote user).
    """
    from suddenly.characters.models import LinkRequest, LinkType, Character
    
    actor_url = activity.get('actor')
    obj = activity.get('object', {})
    
    if obj.get('type') != 'Relationship':
        return
    
    relationship = obj.get('relationship')
    target_url = obj.get('object')  # The NPC being claimed
    
    # Map relationship to LinkType
    link_type = {
        'claim': LinkType.CLAIM,
        'adopt': LinkType.ADOPT,
        'fork': LinkType.FORK,
    }.get(relationship)
    
    if not link_type:
        return
    
    # Get remote requester
    requester, _ = get_or_create_remote_user(actor_url)
    if not requester:
        return
    
    # Find local target character
    target_character = Character.objects.filter(
        ap_id=target_url,
        remote=False,
    ).first()
    
    if not target_character:
        return
    
    # Create link request
    LinkRequest.objects.create(
        type=link_type,
        requester=requester,
        target_character=target_character,
        message=activity.get('summary', ''),
    )
    
    logger.info(f"Created LinkRequest: {link_type} for {target_character.name}")


def handle_accept(activity: dict, actor_type: str, actor_identifier: str):
    """
    Handle Accept activity (our offer was accepted).
    """
    from suddenly.characters.models import LinkRequest, LinkRequestStatus
    
    # The 'object' should be our original Offer activity ID
    offer_id = activity.get('object')
    if not offer_id:
        return
    
    # Extract our request ID from the offer URL
    # Format: .../activities/offer/{uuid}
    if '/activities/offer/' in str(offer_id):
        request_id = offer_id.split('/activities/offer/')[-1]
        try:
            link_request = LinkRequest.objects.get(id=request_id)
            link_request.status = LinkRequestStatus.ACCEPTED
            link_request.response_message = activity.get('summary', '')
            link_request.save()
            logger.info(f"LinkRequest {request_id} accepted")
        except (LinkRequest.DoesNotExist, ValueError):
            pass


def handle_reject(activity: dict, actor_type: str, actor_identifier: str):
    """
    Handle Reject activity (our offer was rejected).
    """
    from suddenly.characters.models import LinkRequest, LinkRequestStatus
    
    offer_id = activity.get('object')
    if not offer_id:
        return
    
    if '/activities/offer/' in str(offer_id):
        request_id = offer_id.split('/activities/offer/')[-1]
        try:
            link_request = LinkRequest.objects.get(id=request_id)
            link_request.status = LinkRequestStatus.REJECTED
            link_request.response_message = activity.get('summary', '')
            link_request.save()
            logger.info(f"LinkRequest {request_id} rejected")
        except (LinkRequest.DoesNotExist, ValueError):
            pass


# =================================================================
# Helper functions
# =================================================================

def get_or_create_remote_user(actor_url: str):
    """
    Fetch and create/update a remote user from their actor URL.
    """
    import httpx
    from suddenly.users.models import User
    
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(
                actor_url,
                headers={"Accept": "application/activity+json"}
            )
            response.raise_for_status()
            actor_data = response.json()
    except Exception as e:
        logger.error(f"Failed to fetch actor {actor_url}: {e}")
        return None, False
    
    username = actor_data.get('preferredUsername', actor_url.split('/')[-1])
    
    user, created = User.objects.update_or_create(
        ap_id=actor_url,
        defaults={
            'username': f"{username}@{actor_url.split('/')[2]}",
            'display_name': actor_data.get('name', username),
            'bio': actor_data.get('summary', ''),
            'remote': True,
            'inbox_url': actor_data.get('inbox'),
            'outbox_url': actor_data.get('outbox'),
            'public_key': actor_data.get('publicKey', {}).get('publicKeyPem', ''),
        }
    )
    
    return user, created


def get_remote_user(actor_url: str):
    """
    Get an existing remote user by actor URL.
    """
    from suddenly.users.models import User
    return User.objects.filter(ap_id=actor_url, remote=True).first()


def get_local_actor(actor_type: str, identifier: str):
    """
    Get a local actor (user, game, or character) by identifier.
    """
    from suddenly.users.models import User
    from suddenly.games.models import Game
    from suddenly.characters.models import Character
    
    if actor_type == 'user':
        return User.objects.filter(username=identifier, remote=False).first()
    elif actor_type == 'game':
        return Game.objects.filter(id=identifier, remote=False).first()
    elif actor_type == 'character':
        return Character.objects.filter(id=identifier, remote=False).first()
    return None
