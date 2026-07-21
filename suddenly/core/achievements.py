"""Achievements (succès) catalogue + unlock service (#153).

Definitions live here in code — versioned, no per-achievement DB row. Each maps
a stat key + threshold to a milestone; unlocking records an ``UnlockedAchievement``
and an ``ACHIEVEMENT`` notification. Evaluated on the Stats page (visit) and on
scene publication (signal). Unlock logic lives in this service, never in a model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from django.utils.functional import _StrPromise

    from suddenly.users.models import User


@dataclass(frozen=True)
class AchievementDef:
    """One achievement: a threshold on a single stat key from ``compute_user_stats``."""

    key: str
    name: _StrPromise
    description: _StrPromise
    icon: str  # Lucide name suffix → rendered as ``i-lucide-<icon>``
    stat: str  # the stats dict key this achievement tracks
    threshold: int

    def is_unlocked(self, stats: dict[str, int]) -> bool:
        return stats.get(self.stat, 0) >= self.threshold


# Initial catalogue (#153) — thresholds are a product proposal, tune freely.
ACHIEVEMENTS: list[AchievementDef] = [
    AchievementDef(
        "first_scene",
        _("Première scène"),
        _("Publier votre première scène."),
        "feather",
        "scenes_published",
        1,
    ),
    AchievementDef(
        "scenes_10", _("Conteur"), _("Publier 10 scènes."), "book-open", "scenes_published", 10
    ),
    AchievementDef(
        "scenes_50", _("Chroniqueur"), _("Publier 50 scènes."), "library", "scenes_published", 50
    ),
    AchievementDef(
        "words_10k", _("Plume affûtée"), _("Écrire 10 000 mots."), "pen-tool", "words", 10_000
    ),
    AchievementDef(
        "words_100k", _("Romancier"), _("Écrire 100 000 mots."), "scroll-text", "words", 100_000
    ),
    AchievementDef(
        "first_character",
        _("Créateur"),
        _("Créer votre premier personnage."),
        "user-plus",
        "characters_created",
        1,
    ),
    AchievementDef(
        "characters_5", _("Troupe"), _("Créer 5 personnages."), "users", "characters_created", 5
    ),
    AchievementDef(
        "first_like_received",
        _("Apprécié"),
        _("Recevoir votre premier like."),
        "heart",
        "likes_received",
        1,
    ),
    AchievementDef(
        "likes_received_100",
        _("Plébiscité"),
        _("Recevoir 100 likes."),
        "heart-handshake",
        "likes_received",
        100,
    ),
    AchievementDef(
        "first_follower",
        _("Suivi"),
        _("Gagner votre premier abonné."),
        "user-check",
        "followers",
        1,
    ),
    AchievementDef(
        "followers_10", _("Entouré"), _("Atteindre 10 abonnés."), "users-round", "followers", 10
    ),
    AchievementDef(
        "first_accepted_link",
        _("Lié"),
        _("Voir une de vos demandes de lien acceptée."),
        "link",
        "accepted_links_made",
        1,
    ),
]

ACHIEVEMENTS_BY_KEY: dict[str, AchievementDef] = {a.key: a for a in ACHIEVEMENTS}


def evaluate_and_unlock(user: User) -> list[str]:
    """Unlock any newly-earned achievements for ``user``. Returns the new keys.

    Idempotent: the ``(user, key)`` unique constraint + ``get_or_create`` guard a
    double unlock; one notification is created per genuinely new unlock. Reads
    fresh stats (the caller invalidates the cache first on a state change).
    """
    from django.utils.translation import gettext

    from suddenly.core.models import Notification, NotificationType, UnlockedAchievement
    from suddenly.core.stats import compute_user_stats

    stats = compute_user_stats(user)
    already = set(UnlockedAchievement.objects.filter(user=user).values_list("key", flat=True))

    new_keys: list[str] = []
    for ach in ACHIEVEMENTS:
        if ach.key in already or not ach.is_unlocked(stats):
            continue
        _row, created = UnlockedAchievement.objects.get_or_create(user=user, key=ach.key)
        if created:
            new_keys.append(ach.key)
            Notification.objects.create(
                recipient=user,
                type=NotificationType.ACHIEVEMENT,
                message=gettext("Succès débloqué : %(name)s") % {"name": ach.name},
            )
    return new_keys


def evaluate_after_change(user_pk: Any) -> None:
    """Invalidate the user's stats cache then re-evaluate achievements (#153).

    Called from state-change signals (scene publication) so a milestone crossed
    by that change unlocks without waiting for a Stats-page visit.
    """
    from suddenly.core.stats import invalidate_user_stats
    from suddenly.users.models import User

    invalidate_user_stats(user_pk)
    user = User.objects.filter(pk=user_pk).first()
    if user is not None:
        evaluate_and_unlock(user)


def achievements_view_model(user: User, stats: dict[str, int]) -> list[dict[str, object]]:
    """Per-achievement display rows (unlocked flag + progress) for the template."""
    from suddenly.core.models import UnlockedAchievement

    unlocked = set(UnlockedAchievement.objects.filter(user=user).values_list("key", flat=True))
    rows: list[dict[str, object]] = []
    for ach in ACHIEVEMENTS:
        current = min(stats.get(ach.stat, 0), ach.threshold)
        rows.append(
            {
                "key": ach.key,
                "name": ach.name,
                "description": ach.description,
                "icon": ach.icon,
                "threshold": ach.threshold,
                "current": current,
                "unlocked": ach.key in unlocked or ach.is_unlocked(stats),
            }
        )
    return rows
