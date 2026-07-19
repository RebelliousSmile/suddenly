from django.apps import AppConfig


class OffersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "suddenly.offers"
    verbose_name = "Offers"

    def ready(self) -> None:
        from . import signals  # noqa: F401
