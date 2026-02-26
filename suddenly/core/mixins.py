"""
Mixins pour les modèles fédérables.

ActivityPubMixin ajoute les champs nécessaires à la fédération ActivityPub.
"""
from django.conf import settings
from django.db import models


class ActivityPubMixin(models.Model):
    """
    Mixin pour les entités fédérables via ActivityPub.

    Attributes:
        ap_id: Identifiant ActivityPub unique (URL), indexé
        inbox: URL de l'inbox (pour acteurs)
        outbox: URL de l'outbox (pour acteurs)
        followers_url: URL de la collection followers
        local: True si créé sur cette instance, indexé
        public_key: Clé publique PEM (signatures HTTP)
        private_key: Clé privée PEM chiffrée (signatures HTTP)
    """

    ap_id = models.URLField(
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Identifiant ActivityPub (URL)",
    )
    inbox = models.URLField(null=True, blank=True, help_text="URL de l'inbox ActivityPub")
    outbox = models.URLField(null=True, blank=True, help_text="URL de l'outbox ActivityPub")
    followers_url = models.URLField(null=True, blank=True, help_text="URL de la collection followers")
    local = models.BooleanField(
        default=True,
        db_index=True,
        help_text="True si créé sur cette instance",
    )
    public_key = models.TextField(null=True, blank=True, help_text="Clé publique PEM pour signatures HTTP")
    private_key = models.TextField(null=True, blank=True, help_text="Clé privée PEM pour signatures HTTP — le chiffrement est à la charge de l'implémentation")

    class Meta:
        abstract = True

    def get_ap_id(self) -> str:
        """
        Retourne l'identifiant ActivityPub de l'entité.

        Pour les entités locales sans ap_id stocké, génère l'URL dynamiquement
        à partir du DOMAIN et de get_absolute_url().

        Returns:
            URL ActivityPub de l'entité

        Note:
            Les classes concrètes doivent implémenter `get_absolute_url()`.
        """
        if self.ap_id:
            return self.ap_id
        protocol = "http" if settings.DEBUG else "https"
        return f"{protocol}://{settings.DOMAIN}{self.get_absolute_url()}"

    def is_remote(self) -> bool:
        """Retourne True si l'entité vient d'une autre instance."""
        return not self.local
