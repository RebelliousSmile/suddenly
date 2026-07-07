"""
ActivityPub serializers for Suddenly.

Converts Django models to ActivityPub JSON-LD format.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings

from suddenly.activitypub.url_utils import absolute_media_url, media_type_for_file

# ActivityPub context.
#
# Type strategy (SUD-F5): Characters serialize as a standard AP ``Person`` so
# generic consumers can display them, with the ``suddenly:Character`` term
# declared for Suddenly-aware peers to recognise the richer type. This dual
# typing is intentional — a strict consumer sees a Person, never an unknown
# type it might reject.
#
# ``sensitive`` is the Mastodon/AS2 Content-Warning flag emitted alongside
# ``summary`` by serialize_report/serialize_quote; it must be declared here or
# strict peers drop it. ``toot`` is declared for the Mastodon namespace.
AP_CONTEXT: list[str | dict[str, str]] = [
    "https://www.w3.org/ns/activitystreams",
    "https://w3id.org/security/v1",
    {
        "suddenly": f"https://{settings.DOMAIN}/ns#",
        "toot": "http://joinmastodon.org/ns#",
        "Character": "suddenly:Character",
        "Game": "suddenly:Game",
        "Quote": "suddenly:Quote",
        "status": "suddenly:status",
        "sheetUrl": "suddenly:sheetUrl",
        # ``gameSystem`` stays a free-form display label (issue D decision: no
        # catalogue). It travels as a Suddenly extension; strict peers ignore it.
        "gameSystem": "suddenly:gameSystem",
        # Narrative meta-model extension (issue F). These terms carry the *shape*
        # of a shared sheet (named traits + value + text actions), NOT shared
        # value semantics — Suddenly never evaluates, in local or federation.
        # A server ignoring this vocabulary drops the block without breaking; the
        # AP body (content/summary) stays readable without the traits.
        "traitSet": "suddenly:traitSet",
        "traits": "suddenly:traits",
        "actions": "suddenly:actions",
        "label": "suddenly:label",
        "value": "suddenly:value",
        "note": "suddenly:note",
        "condition": "suddenly:condition",
        "outcome": "suddenly:outcome",
        "sensitive": "https://www.w3.org/ns/activitystreams#sensitive",
    },
]


def serialize_trait_sets(character: Any) -> list[dict[str, Any]]:
    """Serialize a Character's trait sets as a displayable AP extension.

    Frontier: this is *display data*, never interpreted. Values are emitted
    as-is; no normalization. Returns [] when the character has no trait sets,
    so serialize_character omits the key entirely.
    """
    result: list[dict[str, Any]] = []
    trait_sets = character.trait_sets.prefetch_related("traits", "actions__traits")
    for ts in trait_sets:
        traits: list[dict[str, Any]] = []
        for trait in ts.traits.all():
            entry: dict[str, Any] = {"type": "suddenly:Trait", "name": trait.name}
            if trait.value is not None:
                entry["value"] = trait.value
            if trait.note:
                entry["note"] = trait.note
            traits.append(entry)

        actions: list[dict[str, Any]] = []
        for action in ts.actions.all():
            action_entry: dict[str, Any] = {"type": "suddenly:Action", "name": action.name}
            linked = [t.name for t in action.traits.all()]
            if linked:
                action_entry["traits"] = linked
            if action.condition:
                action_entry["condition"] = action.condition
            if action.outcome:
                action_entry["outcome"] = action.outcome
            actions.append(action_entry)

        result.append(
            {
                "type": "suddenly:TraitSet",
                "label": ts.label,
                "traits": traits,
                "actions": actions,
            }
        )
    return result


def serialize_user(user: Any) -> dict[str, Any]:
    """Serialize a User to ActivityPub Person."""
    actor_url: str = user.actor_url

    data: dict[str, Any] = {
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
            "mediaType": media_type_for_file(user.avatar),
            "url": absolute_media_url(user.avatar),
        }

    if user.public_key:
        data["publicKey"] = {
            "id": f"{actor_url}#main-key",
            "owner": actor_url,
            "publicKeyPem": user.public_key,
        }

    return data


def serialize_game(game: Any) -> dict[str, Any]:
    """Serialize a Game to ActivityPub Group/Service."""
    actor_url: str = game.actor_url

    data: dict[str, Any] = {
        "@context": AP_CONTEXT,
        "type": "Group",
        "id": actor_url,
        "name": game.title,
        "attributedTo": game.owner.actor_url,
        "inbox": f"{actor_url}/inbox",
        "outbox": f"{actor_url}/outbox",
        "followers": f"{actor_url}/followers",
        "url": f"https://{settings.DOMAIN}/games/{game.pk}",
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


def serialize_character(character: Any) -> dict[str, Any]:
    """Serialize a Character to ActivityPub Actor."""
    actor_url: str = character.actor_url

    data: dict[str, Any] = {
        "@context": AP_CONTEXT,
        "type": "Person",  # Characters are treated as Persons in AP
        "id": actor_url,
        "name": character.name,
        "inbox": f"{actor_url}/inbox",
        "outbox": f"{actor_url}/outbox",
        "followers": f"{actor_url}/followers",
        "url": f"https://{settings.DOMAIN}/characters/{character.pk}",
        "published": character.created_at.isoformat(),
        "status": character.status,
        "attributedTo": character.origin_game.actor_url,
    }

    if character.description:
        data["summary"] = character.description

    if character.avatar:
        data["icon"] = {
            "type": "Image",
            "mediaType": media_type_for_file(character.avatar),
            "url": absolute_media_url(character.avatar),
        }

    if character.owner:
        data["owner"] = character.owner.actor_url

    if character.creator:
        data["creator"] = character.creator.actor_url

    if character.sheet_url:
        data["sheetUrl"] = character.sheet_url

    # Narrative meta-model (issue F) — displayable extension, ignored by peers
    # that don't know the suddenly: vocabulary.
    trait_sets = serialize_trait_sets(character)
    if trait_sets:
        data["traitSet"] = trait_sets

    if character.parent:
        data["derivedFrom"] = character.parent.actor_url

    if character.public_key:
        data["publicKey"] = {
            "id": f"{actor_url}#main-key",
            "owner": actor_url,
            "publicKeyPem": character.public_key,
        }

    return data


def serialize_report(report: Any) -> dict[str, Any]:
    """Serialize a Report to ActivityPub Note/Article."""
    report_url = f"https://{settings.DOMAIN}/reports/{report.pk}"

    data: dict[str, Any] = {
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

    # Content Warning (US-30)
    if hasattr(report, "content_warning") and report.content_warning:
        data["summary"] = report.content_warning  # AP CW field
        data["sensitive"] = True

    # Visibility (US-29) — maps to AP addressing
    visibility = getattr(report, "visibility", "public")
    public_url = "https://www.w3.org/ns/activitystreams#Public"
    followers_url = f"{report.author.actor_url}/followers"

    if visibility == "public":
        data["to"] = [public_url]
        data["cc"] = [followers_url]
    elif visibility == "unlisted":
        data["to"] = [followers_url]
        data["cc"] = [public_url]
    elif visibility == "followers":
        data["to"] = [followers_url]
        data["cc"] = []

    # Mentions
    mentions: list[dict[str, str]] = []
    for appearance in report.character_appearances.select_related("character"):
        mentions.append(
            {
                "type": "Mention",
                "href": appearance.character.actor_url,
                "name": f"@{appearance.character.name}",
            }
        )

    if mentions:
        data["tag"] = mentions

    return data


def serialize_quote(quote: Any) -> dict[str, Any]:
    """Serialize a Quote to ActivityPub Note."""
    quote_url = f"https://{settings.DOMAIN}/quotes/{quote.pk}"

    data: dict[str, Any] = {
        "@context": AP_CONTEXT,
        "type": "Note",
        "id": quote.ap_id or quote_url,
        "url": quote_url,
        "attributedTo": quote.character.actor_url,
        "content": f'"{quote.content}"',
        "published": quote.created_at.isoformat(),
    }

    # Content Warning (US-30) — overrides context as summary if CW present
    if hasattr(quote, "content_warning") and quote.content_warning:
        data["summary"] = quote.content_warning
        data["sensitive"] = True
    elif quote.context:
        data["summary"] = quote.context

    if quote.report:
        data["inReplyTo"] = (
            quote.report.ap_id or f"https://{settings.DOMAIN}/reports/{quote.report.pk}"
        )

    return data


def serialize_link_request(link_request: Any) -> dict[str, Any]:
    """Serialize a LinkRequest to ActivityPub Offer."""
    request_url = f"https://{settings.DOMAIN}/link-requests/{link_request.pk}"

    # Determine the object type based on link type
    object_type = {
        "claim": "suddenly:Claim",
        "adopt": "suddenly:Adopt",
        "fork": "suddenly:Fork",
    }.get(link_request.type, "suddenly:Link")

    obj_data: dict[str, Any] = {
        "type": object_type,
        "content": link_request.message,
    }

    data: dict[str, Any] = {
        "@context": AP_CONTEXT,
        "type": "Offer",
        "id": request_url,
        "actor": link_request.requester.actor_url,
        "target": link_request.target_character.actor_url,
        "object": obj_data,
        "published": link_request.created_at.isoformat(),
    }

    if link_request.proposed_character:
        obj_data["proposedCharacter"] = link_request.proposed_character.actor_url

    return data


# Activity serializers


def create_activity(
    activity_type: str,
    actor: Any,
    obj: dict[str, Any] | str,
    target: str | None = None,
) -> dict[str, Any]:
    """Create an ActivityPub activity."""
    activity: dict[str, Any] = {
        "@context": AP_CONTEXT,
        "type": activity_type,
        "actor": actor.actor_url if hasattr(actor, "actor_url") else actor,
        "object": obj,
    }

    if target:
        activity["target"] = target

    return activity


def create_create_activity(actor: Any, obj: dict[str, Any] | str) -> dict[str, Any]:
    """Create a Create activity."""
    return create_activity("Create", actor, obj)


def create_update_activity(actor: Any, obj: dict[str, Any] | str) -> dict[str, Any]:
    """Create an Update activity."""
    return create_activity("Update", actor, obj)


def create_delete_activity(actor: Any, obj_id: str) -> dict[str, Any]:
    """Create a Delete activity."""
    return create_activity("Delete", actor, {"type": "Tombstone", "id": obj_id})


def create_follow_activity(
    actor: Any, target: str, activity_id: str | None = None
) -> dict[str, Any]:
    """Create a Follow activity."""
    activity = create_activity("Follow", actor, target)
    if activity_id:
        activity["id"] = activity_id
    return activity


def create_accept_activity(actor: Any, original_activity: dict[str, Any] | str) -> dict[str, Any]:
    """Create an Accept activity."""
    return create_activity("Accept", actor, original_activity)


def create_reject_activity(actor: Any, original_activity: dict[str, Any] | str) -> dict[str, Any]:
    """Create a Reject activity."""
    return create_activity("Reject", actor, original_activity)


def create_undo_follow_activity(actor: Any, follow_ap_id: str, target: str) -> dict[str, Any]:
    """Create an Undo(Follow) activity.

    Wraps the original Follow as an embedded object so the recipient can
    identify which Follow relationship is being retracted.
    """
    inner_follow: dict[str, Any] = {
        "type": "Follow",
        "id": follow_ap_id,
        "actor": actor.actor_url if hasattr(actor, "actor_url") else actor,
        "object": target,
    }
    return create_activity("Undo", actor, inner_follow)


def create_offer_activity(actor: Any, link_request: Any) -> dict[str, Any]:
    """Create an Offer activity for link requests."""
    return serialize_link_request(link_request)
