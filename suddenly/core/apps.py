from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "suddenly.core"
    verbose_name = "Suddenly Core"

    def ready(self) -> None:
        import suddenly.core.notification_signals  # noqa: F401
