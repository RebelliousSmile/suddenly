from django.apps import AppConfig


class ActivityPubConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "suddenly.activitypub"
    verbose_name = "ActivityPub"

    def ready(self):
        # Import signals to register them
        from . import signals  # noqa: F401
