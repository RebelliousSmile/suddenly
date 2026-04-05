"""
User settings views — federation, data, block/mute (DA-1).

Wireframe 15-settings.md.
"""

from __future__ import annotations

import csv
import io

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse


@login_required
def settings_federation(request: HttpRequest) -> HttpResponse:
    """Federation settings: AP identity, followed instances, blocked instances."""
    return render(request, "users/settings_federation.html")


@login_required
def export_follows_csv(request: HttpRequest) -> HttpResponse:
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
def import_follows_csv(request: HttpRequest) -> HttpResponse:
    """Import follows from Mastodon-compatible CSV (US-32).

    Resolves each address via WebFinger, creates or finds User,
    then creates Follow relationship.
    """
    if request.method == "POST" and request.FILES.get("csv_file"):
        csv_file = request.FILES["csv_file"]
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
def settings_data(request: HttpRequest) -> HttpResponse:
    """Data settings: export/import, migration (US-32)."""
    return render(request, "users/settings_data.html")


@login_required
def block_user(request: HttpRequest) -> HttpResponse:
    """Block a user (US-33). Placeholder — needs Block model."""
    # TODO: implement Block model and filtering
    return redirect(reverse("users:settings_federation"))


def _get_domain() -> str:
    from django.conf import settings

    return getattr(settings, "DOMAIN", "localhost")


def _resolve_and_follow(follower: object, address: str) -> bool:
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
