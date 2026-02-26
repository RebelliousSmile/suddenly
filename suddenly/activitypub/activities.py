"""
ActivityPub activity builders.

Functions to construct ActivityPub activity objects
following the spec: https://www.w3.org/TR/activitypub/
"""

from django.conf import settings
from django.utils import timezone


def get_context():
    """Return the standard ActivityPub context."""
    return [
        "https://www.w3.org/ns/activitystreams",
        "https://w3id.org/security/v1",
    ]


def build_actor(user_or_game_or_character):
    """
    Build an ActivityPub actor object.
    
    Works for User, Game, or Character models.
    """
    obj = user_or_game_or_character
    
    actor = {
        "@context": get_context(),
        "id": obj.actor_url,
        "type": "Person",  # Could be customized per type
        "preferredUsername": getattr(obj, 'username', None) or str(obj.id),
        "inbox": f"{obj.actor_url}/inbox",
        "outbox": f"{obj.actor_url}/outbox",
        "followers": f"{obj.actor_url}/followers",
        "following": f"{obj.actor_url}/following",
    }
    
    # Name
    if hasattr(obj, 'display_name') and obj.display_name:
        actor["name"] = obj.display_name
    elif hasattr(obj, 'name'):
        actor["name"] = obj.name
    elif hasattr(obj, 'title'):
        actor["name"] = obj.title
    
    # Summary/bio
    if hasattr(obj, 'bio') and obj.bio:
        actor["summary"] = obj.bio
    elif hasattr(obj, 'description') and obj.description:
        actor["summary"] = obj.description
    
    # Avatar/icon
    if hasattr(obj, 'avatar') and obj.avatar:
        actor["icon"] = {
            "type": "Image",
            "url": f"https://{settings.DOMAIN}{obj.avatar.url}",
        }
    
    # Public key for HTTP signatures
    if hasattr(obj, 'public_key') and obj.public_key:
        actor["publicKey"] = {
            "id": f"{obj.actor_url}#main-key",
            "owner": obj.actor_url,
            "publicKeyPem": obj.public_key,
        }
    
    return actor


def build_note(report):
    """
    Build an ActivityPub Note object from a Report.
    """
    note = {
        "@context": get_context(),
        "id": report.ap_id or f"{settings.AP_BASE_URL}/reports/{report.id}",
        "type": "Note",
        "attributedTo": report.author.actor_url,
        "content": report.content,
        "published": report.published_at.isoformat() if report.published_at else timezone.now().isoformat(),
        "to": ["https://www.w3.org/ns/activitystreams#Public"],
        "cc": [f"{report.author.actor_url}/followers"],
    }
    
    if report.title:
        note["name"] = report.title
    
    # Add context about the game
    note["context"] = report.game.actor_url
    
    # Add mentioned characters as tags
    mentions = []
    for appearance in report.character_appearances.select_related('character'):
        mentions.append({
            "type": "Mention",
            "href": appearance.character.actor_url,
            "name": f"@{appearance.character.name}",
        })
    
    if mentions:
        note["tag"] = mentions
    
    return note


def build_create_activity(object_type: str, object_id: str):
    """
    Build a Create activity for a new object.
    
    Returns:
        Tuple of (activity_dict, sender_id) or (None, None) if object not found
    """
    activity = {
        "@context": get_context(),
        "type": "Create",
        "published": timezone.now().isoformat(),
        "to": ["https://www.w3.org/ns/activitystreams#Public"],
    }
    
    if object_type == "report":
        from suddenly.games.models import Report
        try:
            report = Report.objects.select_related('author', 'game').get(id=object_id)
            activity["id"] = f"{settings.AP_BASE_URL}/activities/create/{report.id}"
            activity["actor"] = report.author.actor_url
            activity["object"] = build_note(report)
            activity["cc"] = [f"{report.author.actor_url}/followers"]
            return activity, str(report.author.id)
        except Report.DoesNotExist:
            return None, None
    
    elif object_type == "quote":
        from suddenly.characters.models import Quote
        try:
            quote = Quote.objects.select_related('author', 'character').get(id=object_id)
            activity["id"] = f"{settings.AP_BASE_URL}/activities/create/{quote.id}"
            activity["actor"] = quote.author.actor_url
            activity["object"] = {
                "type": "Note",
                "id": f"{settings.AP_BASE_URL}/quotes/{quote.id}",
                "attributedTo": quote.character.actor_url,
                "content": f'"{quote.content}"',
                "context": quote.context,
            }
            return activity, str(quote.author.id)
        except Quote.DoesNotExist:
            return None, None
    
    elif object_type == "character":
        from suddenly.characters.models import Character
        try:
            character = Character.objects.select_related('creator').get(id=object_id)
            activity["id"] = f"{settings.AP_BASE_URL}/activities/create/{character.id}"
            activity["actor"] = character.creator.actor_url
            activity["object"] = build_actor(character)
            return activity, str(character.creator.id)
        except Character.DoesNotExist:
            return None, None
    
    return None, None


def build_offer_activity(link_request):
    """
    Build an Offer activity for a link request.
    
    The Offer activity type is used for claim/adopt/fork requests.
    """
    activity = {
        "@context": get_context(),
        "id": f"{settings.AP_BASE_URL}/activities/offer/{link_request.id}",
        "type": "Offer",
        "actor": link_request.requester.actor_url,
        "published": link_request.created_at.isoformat(),
        "to": [link_request.target_character.creator.actor_url],
        "object": {
            "type": "Relationship",
            "relationship": link_request.type,  # claim, adopt, or fork
            "subject": link_request.requester.actor_url,
            "object": link_request.target_character.actor_url,
        },
        "summary": link_request.message,
    }
    
    # For claims, include the proposed PC
    if link_request.proposed_character:
        activity["object"]["subject"] = link_request.proposed_character.actor_url
    
    return activity


def build_accept_activity(link_request):
    """
    Build an Accept activity for an accepted link request.
    """
    return {
        "@context": get_context(),
        "id": f"{settings.AP_BASE_URL}/activities/accept/{link_request.id}",
        "type": "Accept",
        "actor": link_request.target_character.creator.actor_url,
        "published": link_request.resolved_at.isoformat() if link_request.resolved_at else timezone.now().isoformat(),
        "to": [link_request.requester.actor_url],
        "object": f"{settings.AP_BASE_URL}/activities/offer/{link_request.id}",
        "summary": link_request.response_message or None,
    }


def build_reject_activity(link_request):
    """
    Build a Reject activity for a rejected link request.
    """
    return {
        "@context": get_context(),
        "id": f"{settings.AP_BASE_URL}/activities/reject/{link_request.id}",
        "type": "Reject",
        "actor": link_request.target_character.creator.actor_url,
        "published": link_request.resolved_at.isoformat() if link_request.resolved_at else timezone.now().isoformat(),
        "to": [link_request.requester.actor_url],
        "object": f"{settings.AP_BASE_URL}/activities/offer/{link_request.id}",
        "summary": link_request.response_message or None,
    }


def build_follow_activity(follower, target_actor_url):
    """
    Build a Follow activity.
    """
    return {
        "@context": get_context(),
        "id": f"{settings.AP_BASE_URL}/activities/follow/{follower.id}/{timezone.now().timestamp()}",
        "type": "Follow",
        "actor": follower.actor_url,
        "object": target_actor_url,
        "published": timezone.now().isoformat(),
    }


def build_undo_activity(original_activity_id: str, actor_url: str):
    """
    Build an Undo activity (e.g., for unfollowing).
    """
    return {
        "@context": get_context(),
        "id": f"{settings.AP_BASE_URL}/activities/undo/{timezone.now().timestamp()}",
        "type": "Undo",
        "actor": actor_url,
        "object": original_activity_id,
        "published": timezone.now().isoformat(),
    }
