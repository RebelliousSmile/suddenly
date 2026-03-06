from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "suddenly.users"
    verbose_name = "Users"

    def ready(self) -> None:
        """Import signal handlers."""
        import suddenly.users.signals  # noqa: F401
