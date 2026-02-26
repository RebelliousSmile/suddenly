"""
ActivityPub views for federation discovery and actors.
"""

import json
import re

from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from suddenly.users.models import User
from suddenly.games.models import Game, Report
from suddenly.characters.models import Character, Quote

from .serializers import (
    serialize_user,
    serialize_game,
    serialize_character,
    serialize_report,
    serialize_quote,
)


# =================================================================
# Content negotiation helper
# =================================================================

def is_activitypub_request(request):
    """Check if request accepts ActivityPub content."""
    accept = request.headers.get("Accept", "")
    return (
        "application/activity+json" in accept or
        "application/ld+json" in accept
    )


def activitypub_response(data, status=200):
    """Return an ActivityPub JSON-LD response."""
    return JsonResponse(
        data,
        content_type="application/activity+json",
        status=status
    )


# =================================================================
# Well-known endpoints
# =================================================================

@require_GET
def webfinger(request):
    """
    WebFinger endpoint for discovering ActivityPub actors.
    
    GET /.well-known/webfinger?resource=acct:username@domain
    """
    resource = request.GET.get("resource", "")
    
    if not resource:
        return HttpResponseBadRequest("Missing resource parameter")
    
    # Parse acct: URI
    if resource.startswith("acct:"):
        match = re.match(r"acct:([^@]+)@(.+)", resource)
        if not match:
            return HttpResponseBadRequest("Invalid resource format")
        
        username, domain = match.groups()
        
        if domain != settings.DOMAIN:
            return JsonResponse({"error": "User not found"}, status=404)
        
        try:
            user = User.objects.get(username=username, remote=False)
        except User.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)
        
        actor_url = user.actor_url
        
    elif resource.startswith("https://"):
        actor_url = resource
        user = User.objects.filter(ap_id=resource).first()
        if not user:
            return JsonResponse({"error": "Actor not found"}, status=404)
    else:
        return HttpResponseBadRequest("Invalid resource format")
    
    response = {
        "subject": f"acct:{user.username}@{settings.DOMAIN}",
        "aliases": [actor_url],
        "links": [
            {
                "rel": "self",
                "type": "application/activity+json",
                "href": actor_url,
            },
            {
                "rel": "http://webfinger.net/rel/profile-page",
                "type": "text/html",
                "href": f"https://{settings.DOMAIN}/@{user.username}",
            },
        ],
    }
    
    return JsonResponse(response, content_type="application/jrd+json")


@require_GET
def nodeinfo_index(request):
    """NodeInfo discovery endpoint."""
    return JsonResponse({
        "links": [
            {
                "rel": "http://nodeinfo.diaspora.software/ns/schema/2.0",
                "href": f"https://{settings.DOMAIN}/.well-known/nodeinfo/2.0",
            }
        ]
    })


@require_GET
def nodeinfo(request):
    """NodeInfo 2.0 endpoint with instance metadata."""
    user_count = User.objects.filter(remote=False, is_active=True).count()
    game_count = Game.objects.filter(remote=False, is_public=True).count()
    character_count = Character.objects.filter(remote=False).count()
    report_count = Report.objects.filter(remote=False, status="published").count()
    
    return JsonResponse({
        "version": "2.0",
        "software": {
            "name": "suddenly",
            "version": "0.1.0",
        },
        "protocols": ["activitypub"],
        "usage": {
            "users": {
                "total": user_count,
                "activeMonth": user_count,
                "activeHalfyear": user_count,
            },
            "localPosts": report_count,
        },
        "openRegistrations": True,
        "metadata": {
            "nodeName": settings.SITE_NAME,
            "nodeDescription": settings.SITE_DESCRIPTION,
            "games": game_count,
            "characters": character_count,
        },
    })


# =================================================================
# User actor endpoints
# =================================================================

@require_GET
def user_actor(request, username):
    """
    User actor endpoint.
    
    GET /users/{username}
    """
    try:
        user = User.objects.get(username=username, remote=False)
    except User.DoesNotExist:
        return HttpResponseNotFound("User not found")
    
    # Content negotiation: HTML vs ActivityPub
    if not is_activitypub_request(request):
        # Redirect to profile page for browsers
        from django.shortcuts import redirect
        return redirect(f"/@{username}")
    
    return activitypub_response(serialize_user(user))


@csrf_exempt
@require_POST
def user_inbox(request, username):
    """
    User inbox endpoint for receiving activities.
    
    POST /users/{username}/inbox
    """
    try:
        user = User.objects.get(username=username, remote=False)
    except User.DoesNotExist:
        return HttpResponseNotFound("User not found")
    
    # TODO: Verify HTTP signature
    # TODO: Process incoming activity
    
    try:
        activity = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")
    
    # Queue activity processing
    from .tasks import process_incoming_activity
    process_incoming_activity.delay(user.id, activity)
    
    return JsonResponse({"status": "accepted"}, status=202)


@require_GET
def user_outbox(request, username):
    """
    User outbox endpoint.
    
    GET /users/{username}/outbox
    """
    try:
        user = User.objects.get(username=username, remote=False)
    except User.DoesNotExist:
        return HttpResponseNotFound("User not found")
    
    # Get user's public activities (reports)
    reports = Report.objects.filter(
        author=user,
        status="published",
        game__is_public=True
    ).order_by("-published_at")[:20]
    
    items = [serialize_report(r) for r in reports]
    
    return activitypub_response({
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "OrderedCollection",
        "id": f"{user.actor_url}/outbox",
        "totalItems": reports.count(),
        "orderedItems": items,
    })


@require_GET
def user_followers(request, username):
    """User followers collection."""
    try:
        user = User.objects.get(username=username, remote=False)
    except User.DoesNotExist:
        return HttpResponseNotFound("User not found")
    
    from suddenly.characters.models import Follow
    from django.contrib.contenttypes.models import ContentType
    
    user_ct = ContentType.objects.get_for_model(User)
    followers = Follow.objects.filter(
        content_type=user_ct,
        object_id=user.id
    ).select_related("follower")
    
    return activitypub_response({
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "OrderedCollection",
        "id": f"{user.actor_url}/followers",
        "totalItems": followers.count(),
        "orderedItems": [f.follower.actor_url for f in followers],
    })


# =================================================================
# Game actor endpoints
# =================================================================

@require_GET
def game_actor(request, game_id):
    """Game actor endpoint."""
    try:
        game = Game.objects.get(id=game_id, remote=False, is_public=True)
    except Game.DoesNotExist:
        return HttpResponseNotFound("Game not found")
    
    if not is_activitypub_request(request):
        from django.shortcuts import redirect
        return redirect(f"/games/{game_id}")
    
    return activitypub_response(serialize_game(game))


@csrf_exempt
@require_POST
def game_inbox(request, game_id):
    """Game inbox endpoint."""
    try:
        game = Game.objects.get(id=game_id, remote=False)
    except Game.DoesNotExist:
        return HttpResponseNotFound("Game not found")
    
    try:
        activity = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")
    
    from .tasks import process_incoming_activity
    process_incoming_activity.delay(None, activity, game_id=str(game.id))
    
    return JsonResponse({"status": "accepted"}, status=202)


@require_GET
def game_outbox(request, game_id):
    """Game outbox endpoint."""
    try:
        game = Game.objects.get(id=game_id, remote=False, is_public=True)
    except Game.DoesNotExist:
        return HttpResponseNotFound("Game not found")
    
    reports = game.reports.filter(status="published").order_by("-published_at")[:20]
    items = [serialize_report(r) for r in reports]
    
    return activitypub_response({
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "OrderedCollection",
        "id": f"{game.actor_url}/outbox",
        "totalItems": reports.count(),
        "orderedItems": items,
    })


# =================================================================
# Character actor endpoints
# =================================================================

@require_GET
def character_actor(request, character_id):
    """Character actor endpoint."""
    try:
        character = Character.objects.get(id=character_id, remote=False)
    except Character.DoesNotExist:
        return HttpResponseNotFound("Character not found")
    
    if not is_activitypub_request(request):
        from django.shortcuts import redirect
        return redirect(f"/characters/{character_id}")
    
    return activitypub_response(serialize_character(character))


@csrf_exempt
@require_POST
def character_inbox(request, character_id):
    """Character inbox endpoint."""
    try:
        character = Character.objects.get(id=character_id, remote=False)
    except Character.DoesNotExist:
        return HttpResponseNotFound("Character not found")
    
    try:
        activity = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")
    
    from .tasks import process_incoming_activity
    process_incoming_activity.delay(None, activity, character_id=str(character.id))
    
    return JsonResponse({"status": "accepted"}, status=202)


@require_GET
def character_outbox(request, character_id):
    """Character outbox endpoint - quotes and appearances."""
    try:
        character = Character.objects.get(id=character_id, remote=False)
    except Character.DoesNotExist:
        return HttpResponseNotFound("Character not found")
    
    quotes = character.quotes.filter(visibility="public").order_by("-created_at")[:20]
    items = [serialize_quote(q) for q in quotes]
    
    return activitypub_response({
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "OrderedCollection",
        "id": f"{character.actor_url}/outbox",
        "totalItems": quotes.count(),
        "orderedItems": items,
    })

