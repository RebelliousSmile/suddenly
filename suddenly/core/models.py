"""
Modèles abstraits de base.

Tous les modèles de l'application héritent de BaseModel.
"""
import uuid

from django.db import models


class BaseModel(models.Model):
    """
    Modèle de base avec UUID et timestamps.

    Attributes:
        id: UUID comme clé primaire
        created_at: Date de création (auto)
        updated_at: Date de modification (auto)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.id}>"
