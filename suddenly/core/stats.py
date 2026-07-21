"""User stats aggregation for the Stats & Succès page (#153).

Computed on demand — no denormalized counters. A handful of indexed aggregates
(counts + ``Sum(Length(content))`` for signs) plus a Python word count over the
user's own corpus, memoized in the cache with a short TTL and invalidated on
scene publication. Cheap for a single user's own page; never call inside a loop.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from django.core.cache import cache
from django.db.models import Sum
from django.db.models.functions import Length

if TYPE_CHECKING:
    from suddenly.users.models import User

STATS_CACHE_TTL = 300  # 5 minutes; invalidated on scene publication.


def stats_cache_key(user_pk: Any) -> str:
    return f"user_stats:{user_pk}"


def invalidate_user_stats(user_pk: Any) -> None:
    """Drop the memoized stats for a user (called on a state change)."""
    cache.delete(stats_cache_key(user_pk))


def compute_user_stats(user: User) -> dict[str, int]:
    """Return the user's precise stats, memoized under a short TTL."""
    return cast(
        "dict[str, int]",
        cache.get_or_set(stats_cache_key(user.pk), lambda: _compute(user), STATS_CACHE_TTL),
    )


def _compute(user: User) -> dict[str, int]:
    from django.contrib.contenttypes.models import ContentType

    from suddenly.characters.models import Follow, LinkRequest, LinkRequestStatus
    from suddenly.games.models import Like, Rapport, Recommendation, Report
    from suddenly.messaging.models import DirectMessage
    from suddenly.users.models import User as UserModel

    # Scenes (Report) authored by the user that crossed the public wall.
    scenes_published = Report.objects.filter(author=user).released().count()

    # Text corpus for words/signs: the user's scenes + the posts in their scenes.
    # (Rapport has no user author — attribution is via report.author; a co-player's
    # post in your scene counts for you, the scene author. Assumed limitation.)
    authored_reports = Report.objects.filter(author=user)
    authored_rapports = Rapport.objects.filter(report__author=user)

    report_chars = authored_reports.aggregate(n=Sum(Length("content")))["n"] or 0
    rapport_chars = authored_rapports.aggregate(n=Sum(Length("content")))["n"] or 0
    signs = int(report_chars) + int(rapport_chars)

    words = 0
    for content in authored_reports.values_list("content", flat=True):
        words += len((content or "").split())
    for content in authored_rapports.values_list("content", flat=True):
        words += len((content or "").split())

    user_ct = ContentType.objects.get_for_model(UserModel)

    return {
        "scenes_published": scenes_published,
        "posts": authored_rapports.count(),
        "signs": signs,
        "words": words,
        "characters_created": user.created_characters.count(),
        "games": user.games.count(),
        "likes_given": Like.objects.filter(user=user).count(),
        "likes_received": Like.objects.filter(report__author=user).count(),
        "recommendations_given": Recommendation.objects.filter(user=user).count(),
        "recommendations_received": Recommendation.objects.filter(report__author=user).count(),
        "followers": Follow.objects.filter(content_type=user_ct, object_id=user.id).count(),
        "following": Follow.objects.filter(follower=user).count(),
        "accepted_links_made": LinkRequest.objects.filter(
            requester=user, status=LinkRequestStatus.ACCEPTED
        ).count(),
        "accepted_links_received": LinkRequest.objects.filter(
            target_character__creator=user, status=LinkRequestStatus.ACCEPTED
        ).count(),
        "messages_sent": DirectMessage.objects.filter(sender=user).count(),
    }
