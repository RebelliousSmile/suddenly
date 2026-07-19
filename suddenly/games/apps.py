from django.apps import AppConfig


class GamesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "suddenly.games"
    verbose_name = "Games"

    def ready(self) -> None:
        from django.db.models.signals import post_delete, post_save

        from suddenly.games.models import GameCast
        from suddenly.games.signals import gamecast_post_delete, gamecast_post_save

        post_save.connect(
            gamecast_post_save,
            sender=GameCast,
            dispatch_uid="games.cast_follow_sync",
        )
        post_delete.connect(
            gamecast_post_delete,
            sender=GameCast,
            dispatch_uid="games.cast_follow_teardown",
        )
