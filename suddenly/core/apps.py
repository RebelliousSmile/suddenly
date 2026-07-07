from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "suddenly.core"
    verbose_name = "Suddenly Core"

    def ready(self) -> None:
        # Cache invalidation signals — every connect MUST carry a unique
        # dispatch_uid to survive --reuse-db and dev autoreload (handlers stay
        # connected across reloads, producing duplicates without uid).
        # Renaming a handler? Rename its dispatch_uid too — stale handlers stay
        # connected in the dev process otherwise.
        from django.db.models.signals import m2m_changed, post_delete, post_save

        import suddenly.core.notification_signals  # noqa: F401
        from suddenly.activitypub.models import FederatedServer
        from suddenly.characters.models import Character
        from suddenly.core.cache_invalidation import (
            invalidate_explorer_tags_character,
            invalidate_explorer_tags_game,
            invalidate_instance_stats,
            invalidate_recent_public_reports,
        )
        from suddenly.games.models import Game, Report
        from suddenly.users.models import User

        m2m_changed.connect(
            invalidate_explorer_tags_character,
            sender=Character.tags.through,
            dispatch_uid="suddenly.cache.invalidate_explorer_tags_character",
        )
        m2m_changed.connect(
            invalidate_explorer_tags_game,
            sender=Game.tags.through,
            dispatch_uid="suddenly.cache.invalidate_explorer_tags_game",
        )
        post_save.connect(
            invalidate_recent_public_reports,
            sender=Report,
            dispatch_uid="suddenly.cache.invalidate_recent_public_reports_save",
        )
        post_delete.connect(
            invalidate_recent_public_reports,
            sender=Report,
            dispatch_uid="suddenly.cache.invalidate_recent_public_reports_delete",
        )
        for model in (User, Character, Report, FederatedServer):
            post_save.connect(
                invalidate_instance_stats,
                sender=model,
                dispatch_uid=f"suddenly.cache.invalidate_instance_stats_save_{model._meta.label_lower}",
            )
            post_delete.connect(
                invalidate_instance_stats,
                sender=model,
                dispatch_uid=f"suddenly.cache.invalidate_instance_stats_delete_{model._meta.label_lower}",
            )
