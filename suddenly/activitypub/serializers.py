"""
ActivityPub serializers for Suddenly.

Converts Django models to ActivityPub JSON-LD format.
"""

from django.conf import settings
from django.urls import reverse


# ActivityPub context
AP_CONTEXT = [
    "https://www.w3.org/ns/activitystreams",
    "https://w3id.org/security/v1",
    {
        "suddenly": f"https://{settings.DOMAIN}/ns#",
        "Character": "suddenly:Character",
        "Game": "suddenly:Game",
        "Quote": "suddenly:Quote",
        "status": "suddenly:status",
        "sheetUrl": "suddenly:sheetUrl",
        "gameSystem": "suddenly:gameSystem",
    }
]


def serialize_user(user):
    """Serialize a User to ActivityPub Person."""
    actor_url = user.actor_url
    
    data = {
        "@context": AP_CONTEXT,
        "type": "Person",
        "id": actor_url,
        "preferredUsername": user.username,
        "name": user.get_display_name(),
        "inbox": f"{actor_url}/inbox",
        "outbox": f"{actor_url}/outbox",
        "followers": f"{actor_url}/followers",
        "following": f"{actor_url}/following",
        "url": f"https://{settings.DOMAIN}/@{user.username}",
        "published": user.created_at.isoformat(),
    }
    
    if user.bio:
        data["summary"] = user.bio
    
    if user.avatar:
        data["icon"] = {
            "type": "Image",
            "mediaType": "image/jpeg",
            "url": f"https://{settings.DOMAIN}{user.avatar.url}",
        }
    
    if user.public_key:
        data["publicKey"] = {
            "id": f"{actor_url}#main-key",
            "owner": actor_url,
            "publicKeyPem": user.public_key,
        }
    
    return data


def serialize_game(game):
    """Serialize a Game to ActivityPub Group/Service."""
    actor_url = game.actor_url
    
    data = {
        "@context": AP_CONTEXT,
        "type": "Group",
        "id": actor_url,
        "name": game.title,
        "attributedTo": game.owner.actor_url,
        "inbox": f"{actor_url}/inbox",
        "outbox": f"{actor_url}/outbox",
        "followers": f"{actor_url}/followers",
        "url": f"https://{settings.DOMAIN}/games/{game.id}",
        "published": game.created_at.isoformat(),
    }
    
    if game.description:
        data["summary"] = game.description
    
    if game.game_system:
        data["gameSystem"] = game.game_system
    
    if game.public_key:
        data["publicKey"] = {
            "id": f"{actor_url}#main-key",
            "owner": actor_url,
            "publicKeyPem": game.public_key,
        }
    
    return data


def serialize_character(character):
    """Serialize a Character to ActivityPub Actor."""
    actor_url = character.actor_url
    
    data = {
        "@context": AP_CONTEXT,
        "type": "Person",  # Characters are treated as Persons in AP
        "id": actor_url,
        "name": character.name,
        "inbox": f"{actor_url}/inbox",
        "outbox": f"{actor_url}/outbox",
        "followers": f"{actor_url}/followers",
        "url": f"https://{settings.DOMAIN}/characters/{character.id}",
        "published": character.created_at.isoformat(),
        "status": character.status,
        "attributedTo": character.origin_game.actor_url,
    }
    
    if character.description:
        data["summary"] = character.description
    
    if character.avatar:
        data["icon"] = {
            "type": "Image",
            "mediaType": "image/jpeg",
            "url": f"https://{settings.DOMAIN}{character.avatar.url}",
        }
    
    if character.owner:
        data["owner"] = character.owner.actor_url
    
    if character.creator:
        data["creator"] = character.creator.actor_url
    
    if character.sheet_url:
        data["sheetUrl"] = character.sheet_url
    
    if character.parent:
        data["derivedFrom"] = character.parent.actor_url
    
    if character.public_key:
        data["publicKey"] = {
            "id": f"{actor_url}#main-key",
            "owner": actor_url,
            "publicKeyPem": character.public_key,
        }
    
    return data


def serialize_report(report):
    """Serialize a Report to ActivityPub Note/Article."""
    report_url = f"https://{settings.DOMAIN}/reports/{report.id}"
    
    data = {
        "@context": AP_CONTEXT,
        "type": "Article",
        "id": report.ap_id or report_url,
        "url": report_url,
        "attributedTo": report.author.actor_url,
        "context": report.game.actor_url,
        "content": report.content,
        "published": (report.published_at or report.created_at).isoformat(),
    }
    
    if report.title:
        data["name"] = report.title
    
    # Mentions
    mentions = []
    for appearance in report.character_appearances.select_related("character"):
        mentions.append({
            "type": "Mention",
            "href": appearance.character.actor_url,
            "name": f"@{appearance.character.name}",
        })
    
    if mentions:
        data["tag"] = mentions
    
    return data


def serialize_quote(quote):
    """Serialize a Quote to ActivityPub Note."""
    quote_url = f"https://{settings.DOMAIN}/quotes/{quote.id}"
    
    data = {
        "@context": AP_CONTEXT,
        "type": "Note",
        "id": quote.ap_id or quote_url,
        "url": quote_url,
        "attributedTo": quote.character.actor_url,
        "content": f'"{quote.content}"',
        "published": quote.created_at.isoformat(),
    }
    
    if quote.context:
        data["summary"] = quote.context
    
    if quote.report:
        data["inReplyTo"] = quote.report.ap_id or f"https://{settings.DOMAIN}/reports/{quote.report.id}"
    
    return data


def serialize_link_request(link_request):
    """Serialize a LinkRequest to ActivityPub Offer."""
    request_url = f"https://{settings.DOMAIN}/link-requests/{link_request.id}"
    
    # Determine the object type based on link type
    object_type = {
        "claim": "suddenly:Claim",
        "adopt": "suddenly:Adopt",
        "fork": "suddenly:Fork",
    }.get(link_request.type, "suddenly:Link")
    
    data = {
        "@context": AP_CONTEXT,
        "type": "Offer",
        "id": request_url,
        "actor": link_request.requester.actor_url,
        "target": link_request.target_character.actor_url,
        "object": {
            "type": object_type,
            "content": link_request.message,
        },
        "published": link_request.created_at.isoformat(),
    }
    
    if link_request.proposed_character:
        data["object"]["proposedCharacter"] = link_request.proposed_character.actor_url
    
    return data


# Activity serializers

def create_activity(activity_type, actor, obj, target=None):
    """Create an ActivityPub activity."""
    activity = {
        "@context": AP_CONTEXT,
        "type": activity_type,
        "actor": actor.actor_url if hasattr(actor, "actor_url") else actor,
        "object": obj,
    }
    
    if target:
        activity["target"] = target
    
    return activity


def create_create_activity(actor, obj):
    """Create a Create activity."""
    return create_activity("Create", actor, obj)


def create_update_activity(actor, obj):
    """Create an Update activity."""
    return create_activity("Update", actor, obj)


def create_delete_activity(actor, obj_id):
    """Create a Delete activity."""
    return create_activity("Delete", actor, {"type": "Tombstone", "id": obj_id})


def create_follow_activity(actor, target):
    """Create a Follow activity."""
    return create_activity("Follow", actor, target)


def create_accept_activity(actor, original_activity):
    """Create an Accept activity."""
    return create_activity("Accept", actor, original_activity)


def create_reject_activity(actor, original_activity):
    """Create a Reject activity."""
    return create_activity("Reject", actor, original_activity)


def create_offer_activity(actor, link_request):
    """Create an Offer activity for link requests."""
    return serialize_link_request(link_request)
