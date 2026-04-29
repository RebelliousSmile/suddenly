"""
User settings views — federation, data, block/mute (DA-1).

Wireframe 15-settings.md.
"""

from __future__ import annotations

import csv
import io
import json

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_datetime

from suddenly.core.types import AuthenticatedRequest
from suddenly.users.forms import PreferencesForm
from suddenly.users.models import User


@login_required
def settings_preferences(request: AuthenticatedRequest) -> HttpResponse:
    """Language and interface preferences."""
    if request.method == "POST":
        form = PreferencesForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            from django.contrib import messages

            messages.success(request, "Preferences saved.")
            return redirect(reverse("users:settings_preferences"))
    else:
        form = PreferencesForm(instance=request.user)
    try:
        default_bg = request.user.default_character_background
        bg_url = default_bg.url if default_bg else ""
    except ValueError:
        bg_url = ""
    return render(request, "users/settings_preferences.html", {"form": form, "bg_url": bg_url})


@login_required
def settings_federation(request: AuthenticatedRequest) -> HttpResponse:
    """Federation settings: AP identity, followed instances, blocked instances."""
    return render(request, "users/settings_federation.html")


@login_required
def export_follows_csv(request: AuthenticatedRequest) -> HttpResponse:
    """Export follows as Mastodon-compatible CSV (US-32)."""
    from django.contrib.contenttypes.models import ContentType

    from suddenly.characters.models import Follow
    from suddenly.users.models import User

    user_ct = ContentType.objects.get_for_model(User)
    follows = (
        Follow.objects.filter(follower=request.user, content_type=user_ct)
        .select_related("follower")
        .values_list("object_id", flat=True)
    )

    followed_users = User.objects.filter(pk__in=follows)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Account address", "Show boosts", "Notify on new posts", "Languages"])
    for u in followed_users:
        address = u.ap_id or f"{u.username}@{_get_domain()}"
        writer.writerow([address, "true", "false", ""])

    response = HttpResponse(output.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="follows.csv"'
    return response


@login_required
def import_follows_csv(request: AuthenticatedRequest) -> HttpResponse:
    """Import follows from Mastodon-compatible CSV (US-32).

    Resolves each address via WebFinger, creates or finds User,
    then creates Follow relationship.
    """
    if request.method == "POST" and request.FILES.get("csv_file"):
        from django.core.files.uploadedfile import UploadedFile

        csv_file = request.FILES.get("csv_file")
        if not isinstance(csv_file, UploadedFile):
            return render(request, "users/settings_data.html")
        decoded = csv_file.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(decoded))

        imported = 0
        errors = 0
        for row in reader:
            address = row.get("Account address", "").strip()
            if not address:
                continue

            user_to_follow = _resolve_and_follow(request.user, address)
            if user_to_follow:
                imported += 1
            else:
                errors += 1

        return render(
            request,
            "users/settings_data.html",
            {"import_success": True, "imported_count": imported, "import_errors": errors},
        )

    return render(request, "users/settings_data.html")


@login_required
def settings_data(request: AuthenticatedRequest) -> HttpResponse:
    """Data settings: export/import, migration (US-32)."""
    from suddenly.games.models import Game

    has_games = Game.objects.filter(owner=request.user, remote=False).exists()
    return render(request, "users/settings_data.html", {"has_games": has_games})


@login_required
def export_games(request: AuthenticatedRequest) -> FileResponse:
    """Export all games owned by the user as JSON (US-32)."""
    from suddenly.games.models import Game

    games = Game.objects.filter(owner=request.user, remote=False).order_by("created_at")
    data = [
        {
            "title": g.title,
            "description": g.description,
            "game_system": g.game_system,
            "is_public": g.is_public,
            "created_at": g.created_at.isoformat(),
        }
        for g in games
    ]
    content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    return FileResponse(
        io.BytesIO(content),
        content_type="application/json",
        as_attachment=True,
        filename="suddenly-games.json",
    )


@login_required
def export_characters(request: AuthenticatedRequest) -> FileResponse:
    """Export all characters created by the user as JSON (US-32)."""
    from suddenly.characters.models import Character

    characters = (
        Character.objects.filter(creator=request.user, remote=False)
        .select_related("origin_game")
        .order_by("created_at")
    )
    data = [
        {
            "name": c.name,
            "description": c.description,
            "status": c.status,
            "sheet_url": c.sheet_url or None,
            "origin_game_title": c.origin_game.title if c.origin_game_id else None,
            "created_at": c.created_at.isoformat(),
        }
        for c in characters
    ]
    content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    return FileResponse(
        io.BytesIO(content),
        content_type="application/json",
        as_attachment=True,
        filename="suddenly-characters.json",
    )


def _data_ctx(request: AuthenticatedRequest) -> dict[str, object]:
    """Base context for settings_data.html — resolves has_games once."""
    from suddenly.games.models import Game

    return {"has_games": Game.objects.filter(owner=request.user, remote=False).exists()}


@login_required
def import_games(request: AuthenticatedRequest) -> HttpResponse:
    """Import games from a JSON file (US-32).

    Deduplication: skip if (title, created_at) already exists for this owner.
    Preserves original created_at via queryset .update() after creation.
    """
    if request.method != "POST":
        return render(request, "users/settings_data.html", _data_ctx(request))

    from django.core.files.uploadedfile import UploadedFile

    from suddenly.games.models import Game

    games_file = request.FILES.get("games_file")
    if not isinstance(games_file, UploadedFile):
        return render(request, "users/settings_data.html", _data_ctx(request))

    try:
        data = json.loads(games_file.read().decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return render(
            request, "users/settings_data.html", {**_data_ctx(request), "games_import_error": True}
        )

    if not isinstance(data, list):
        return render(
            request, "users/settings_data.html", {**_data_ctx(request), "games_import_error": True}
        )

    imported = 0
    skipped = 0

    for item in data:
        if not isinstance(item, dict):
            skipped += 1
            continue

        title = item.get("title", "").strip()
        created_at_raw = item.get("created_at", "")
        if not title:
            skipped += 1
            continue

        created_at = parse_datetime(created_at_raw) if created_at_raw else None

        if (
            created_at
            and Game.objects.filter(owner=request.user, title=title, created_at=created_at).exists()
        ):
            skipped += 1
            continue

        game = Game.objects.create(
            title=title,
            description=item.get("description", ""),
            game_system=item.get("game_system", ""),
            is_public=bool(item.get("is_public", True)),
            owner=request.user,
            remote=False,
        )
        if created_at:
            Game.objects.filter(pk=game.pk).update(created_at=created_at)
        imported += 1

    return render(
        request,
        "users/settings_data.html",
        {
            **_data_ctx(request),
            "games_import_success": True,
            "games_imported": imported,
            "games_skipped": skipped,
        },
    )


@login_required
def import_characters(request: AuthenticatedRequest) -> HttpResponse:
    """Import characters from a JSON file (US-32).

    Deduplication: skip if (name, created_at) already exists for this creator.
    origin_game resolved by title among user's games; skipped if not found (non-nullable FK).
    """
    if request.method != "POST":
        return render(request, "users/settings_data.html", _data_ctx(request))

    from django.core.files.uploadedfile import UploadedFile

    from suddenly.characters.models import Character
    from suddenly.games.models import Game

    characters_file = request.FILES.get("characters_file")
    if not isinstance(characters_file, UploadedFile):
        return render(request, "users/settings_data.html", _data_ctx(request))

    try:
        data = json.loads(characters_file.read().decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return render(
            request, "users/settings_data.html", {**_data_ctx(request), "chars_import_error": True}
        )

    if not isinstance(data, list):
        return render(
            request, "users/settings_data.html", {**_data_ctx(request), "chars_import_error": True}
        )

    user_games: dict[str, Game] = {
        g.title: g for g in Game.objects.filter(owner=request.user, remote=False)
    }

    imported = 0
    skipped = 0

    for item in data:
        if not isinstance(item, dict):
            skipped += 1
            continue

        name = item.get("name", "").strip()
        created_at_raw = item.get("created_at", "")
        if not name:
            skipped += 1
            continue

        origin_game = user_games.get(item.get("origin_game_title") or "")
        if origin_game is None:
            skipped += 1
            continue

        created_at = parse_datetime(created_at_raw) if created_at_raw else None

        if (
            created_at
            and Character.objects.filter(
                creator=request.user, name=name, created_at=created_at
            ).exists()
        ):
            skipped += 1
            continue

        status = item.get("status", "npc")
        character = Character.objects.create(
            name=name,
            description=item.get("description", ""),
            status=status,
            sheet_url=item.get("sheet_url") or None,
            origin_game=origin_game,
            creator=request.user,
            owner=request.user if status == "pc" else None,
            remote=False,
        )
        if created_at:
            Character.objects.filter(pk=character.pk).update(created_at=created_at)
        imported += 1

    return render(
        request,
        "users/settings_data.html",
        {
            **_data_ctx(request),
            "chars_import_success": True,
            "chars_imported": imported,
            "chars_skipped": skipped,
        },
    )


@login_required
def block_user(request: AuthenticatedRequest) -> HttpResponse:
    """Block a user (US-33). Placeholder — needs Block model."""
    # TODO: implement Block model and filtering
    return redirect(reverse("users:settings_federation"))


def _get_domain() -> str:
    from django.conf import settings

    return getattr(settings, "DOMAIN", "localhost")


def _resolve_and_follow(follower: User, address: str) -> bool:
    """Resolve a @user@instance address and create Follow. Returns True on success."""
    import logging

    import httpx
    from django.contrib.contenttypes.models import ContentType

    from suddenly.characters.models import Follow
    from suddenly.users.models import User

    logger = logging.getLogger(__name__)

    # Parse address
    address = address.lstrip("@")
    parts = address.split("@")

    if len(parts) == 1:
        # Local user
        target = User.objects.filter(username=parts[0], is_active=True, remote=False).first()
    elif len(parts) == 2:
        username, domain = parts
        # Check if already known
        target = User.objects.filter(ap_id__icontains=f"/{username}", remote=True).first()
        if not target:
            # WebFinger lookup
            try:
                url = f"https://{domain}/.well-known/webfinger?resource=acct:{address}"
                with httpx.Client(timeout=10) as client:
                    resp = client.get(url, headers={"Accept": "application/jrd+json"})
                if resp.status_code != 200:
                    return False

                data = resp.json()
                actor_url = None
                for link in data.get("links", []):
                    if link.get("rel") == "self" and "activity" in link.get("type", ""):
                        actor_url = link["href"]
                        break

                if not actor_url:
                    return False

                # Create remote user
                from suddenly.activitypub.tasks import get_or_create_remote_user

                target = get_or_create_remote_user(actor_url)
            except Exception:
                logger.warning("WebFinger failed for %s", address, exc_info=True)
                return False
    else:
        return False

    if not target:
        return False

    # Create follow
    ct = ContentType.objects.get_for_model(User)
    _, created = Follow.objects.get_or_create(
        follower=follower,
        content_type=ct,
        object_id=target.pk,
    )
    return created
