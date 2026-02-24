# Tâche 02 : App Core

**Durée estimée** : 30 min
**Phase** : 1 - Fondations
**Statut** : [ ] À faire
**Dépend de** : 01-config-django

---

## Objectif

Créer l'app `core` avec les modèles abstraits `BaseModel` et `ActivityPubMixin` utilisés par toutes les autres apps.

## Prérequis

- Tâche 01 complétée
- Structure config/ en place

## Fichiers à Créer

```
apps/core/
├── __init__.py
├── apps.py
├── models.py          # BaseModel avec UUID
├── mixins.py          # ActivityPubMixin
└── utils.py           # Utilitaires communs
```

## Étapes

### 1. Créer la structure

```bash
mkdir -p apps/core
touch apps/core/__init__.py
```

### 2. Créer apps/core/apps.py

```python
"""Core app configuration."""
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core'
```

### 3. Créer apps/core/models.py

```python
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

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.id}>"
```

### 4. Créer apps/core/mixins.py

```python
"""
Mixins pour les modèles.

ActivityPubMixin ajoute les champs nécessaires à la fédération.
Ces champs sont présents dès le début mais utilisés en Phase 4.
"""
from django.conf import settings
from django.db import models


class ActivityPubMixin(models.Model):
    """
    Mixin pour les entités fédérables via ActivityPub.

    Les champs sont nullable car :
    - Les entités locales génèrent leur ap_id dynamiquement
    - Les entités distantes ont ces champs remplis

    Attributes:
        ap_id: Identifiant ActivityPub unique (URL)
        inbox: URL de l'inbox (pour acteurs)
        outbox: URL de l'outbox (pour acteurs)
        followers_url: URL de la collection followers
        local: True si créé sur cette instance
        public_key: Clé publique PEM (signatures HTTP)
        private_key: Clé privée PEM chiffrée (signatures HTTP)
    """

    ap_id = models.URLField(
        unique=True,
        null=True,
        blank=True,
        help_text="Identifiant ActivityPub (URL)"
    )
    inbox = models.URLField(
        null=True,
        blank=True,
        help_text="URL de l'inbox ActivityPub"
    )
    outbox = models.URLField(
        null=True,
        blank=True,
        help_text="URL de l'outbox ActivityPub"
    )
    followers_url = models.URLField(
        null=True,
        blank=True,
        help_text="URL de la collection followers"
    )
    local = models.BooleanField(
        default=True,
        help_text="True si créé sur cette instance"
    )
    public_key = models.TextField(
        null=True,
        blank=True,
        help_text="Clé publique PEM pour signatures HTTP"
    )
    private_key = models.TextField(
        null=True,
        blank=True,
        help_text="Clé privée PEM (chiffrée) pour signatures HTTP"
    )

    class Meta:
        abstract = True

    def get_ap_id(self) -> str:
        """
        Retourne l'identifiant ActivityPub.

        Pour les entités locales sans ap_id, génère l'URL à partir
        du DOMAIN et de get_absolute_url().

        Returns:
            URL ActivityPub de l'entité
        """
        if self.ap_id:
            return self.ap_id
        # Utilise HTTPS sauf en développement
        protocol = 'http' if settings.DEBUG else 'https'
        return f"{protocol}://{settings.DOMAIN}{self.get_absolute_url()}"

    def is_remote(self) -> bool:
        """Retourne True si l'entité vient d'une autre instance."""
        return not self.local
```

### 5. Créer apps/core/utils.py

```python
"""
Utilitaires communs.
"""
from django.utils.text import slugify as django_slugify


def generate_unique_slug(model_class, value: str, instance=None) -> str:
    """
    Génère un slug unique pour un modèle.

    Args:
        model_class: La classe du modèle
        value: La valeur à slugifier
        instance: Instance existante (pour update)

    Returns:
        Slug unique
    """
    base_slug = django_slugify(value)
    slug = base_slug
    counter = 1

    # Exclure l'instance actuelle si update
    queryset = model_class.objects.all()
    if instance and instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    while queryset.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug
```

### 6. Mettre à jour apps/core/__init__.py

```python
"""
Core application.

Provides BaseModel and ActivityPubMixin for all models.
"""
default_app_config = 'apps.core.apps.CoreConfig'
```

## Validation

- [ ] `python -c "from apps.core.models import BaseModel"` fonctionne
- [ ] `python -c "from apps.core.mixins import ActivityPubMixin"` fonctionne
- [ ] Les classes sont bien abstraites (`abstract = True`)
- [ ] Type hints présents

## Notes

- Ces modèles sont **abstraits** — ils ne créent pas de tables
- ActivityPubMixin est prêt pour la Phase 4 mais inutilisé pour l'instant
- `get_absolute_url()` devra être implémenté par chaque modèle concret

## Références

- `documentation/models/README.md` — Conventions et BaseModel
- `documentation/api/activitypub.md` — Champs ActivityPub
