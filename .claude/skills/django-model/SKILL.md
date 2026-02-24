---
name: django-model
description: Use when creating Django models, adding fields, creating migrations, or modifying database schema. Ensures UUID primary keys, proper indexes, and ActivityPub compatibility.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Django Model Skill

Skill pour créer et modifier des modèles Django selon les conventions Suddenly.

## Conventions Obligatoires

### 1. Héritage BaseModel

Tous les modèles héritent de `BaseModel` :

```python
from core.models import BaseModel

class MyModel(BaseModel):
    # UUID pk + created_at + updated_at automatiques
    pass
```

### 2. Entités fédérables

Ajouter `ActivityPubMixin` si l'entité doit être fédérée :

```python
from core.models import BaseModel, ActivityPubMixin

class Character(BaseModel, ActivityPubMixin):
    # ap_id, inbox, outbox, local automatiques
    pass
```

### 3. Nommage

| Élément | Convention | Exemple |
|---------|------------|---------|
| Classe | PascalCase | `CharacterLink` |
| Table | `app_model` | `characters_characterlink` |
| Champ FK | `model_id` | `owner_id` |
| Related name | Pluriel | `characters`, `reports` |

## Template Modèle Standard

```python
"""
Module: apps/{app}/models.py
Description: [Description du modèle]
"""
from django.db import models
from django.urls import reverse
from core.models import BaseModel


class {ModelName}(BaseModel):
    """[Description courte]."""

    # Champs
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    # Relations
    owner = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='{model_plural}'
    )

    # Métadonnées
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = '{app}_{model}'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner']),
            models.Index(fields=['slug']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'slug'],
                name='unique_{model}_slug_per_owner'
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse('{app}:{model}_detail', kwargs={'slug': self.slug})
```

## Template Modèle ActivityPub

```python
from django.db import models
from django.conf import settings
from core.models import BaseModel, ActivityPubMixin


class {ModelName}(BaseModel, ActivityPubMixin):
    """[Description] - Acteur/Objet ActivityPub."""

    # Champs métier
    name = models.CharField(max_length=255)
    # ...

    # Clés cryptographiques (si Acteur)
    public_key = models.TextField(null=True, blank=True)
    private_key = models.TextField(null=True, blank=True)

    class Meta:
        db_table = '{app}_{model}'
        indexes = [
            models.Index(fields=['ap_id']),
            models.Index(fields=['local']),
        ]

    def get_ap_id(self) -> str:
        """Retourne l'identifiant ActivityPub."""
        if self.ap_id:
            return self.ap_id
        return f"https://{settings.DOMAIN}{self.get_absolute_url()}"

    def to_activitypub(self) -> dict:
        """Sérialise en ActivityPub."""
        return {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                {"suddenly": "https://suddenly.social/ns#"}
            ],
            "id": self.get_ap_id(),
            "type": "Person",  # ou Group, Article, Note...
            "name": self.name,
            # ...
        }
```

## Template Enum (Choices)

```python
from django.db import models


class {EnumName}(models.TextChoices):
    """[Description des choix]."""
    OPTION_A = 'OPTION_A', 'Label Option A'
    OPTION_B = 'OPTION_B', 'Label Option B'
    OPTION_C = 'OPTION_C', 'Label Option C'
```

## Template Modèle de Liaison (M2M through)

```python
class {ModelA}{ModelB}(BaseModel):
    """Liaison entre {ModelA} et {ModelB}."""

    {model_a} = models.ForeignKey(
        '{ModelA}',
        on_delete=models.CASCADE,
        related_name='{model_b}_links'
    )
    {model_b} = models.ForeignKey(
        '{ModelB}',
        on_delete=models.CASCADE,
        related_name='{model_a}_links'
    )

    # Champs additionnels
    role = models.CharField(max_length=50, blank=True)
    context = models.TextField(blank=True)

    class Meta:
        db_table = '{app}_{model_a}_{model_b}'
        unique_together = [['{model_a}', '{model_b}']]
        indexes = [
            models.Index(fields=['{model_a}']),
            models.Index(fields=['{model_b}']),
        ]
```

## Checklist Création Modèle

Avant de créer :
- [ ] Vérifier que le modèle n'existe pas déjà
- [ ] Identifier l'app appropriée
- [ ] Déterminer si fédérable (ActivityPubMixin)

Après création :
- [ ] Créer la migration : `python manage.py makemigrations {app}`
- [ ] Vérifier la migration générée
- [ ] Appliquer : `python manage.py migrate`
- [ ] Ajouter au `admin.py` si pertinent
- [ ] Mettre à jour `documentation/models/README.md`

## Migrations

### Créer une migration

```bash
python manage.py makemigrations {app} --name {description}
```

### Migration avec données

```python
# migrations/000X_populate_data.py
from django.db import migrations


def populate_data(apps, schema_editor):
    Model = apps.get_model('{app}', '{Model}')
    Model.objects.create(name='Default')


def reverse_populate(apps, schema_editor):
    Model = apps.get_model('{app}', '{Model}')
    Model.objects.filter(name='Default').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('{app}', '000X_previous'),
    ]

    operations = [
        migrations.RunPython(populate_data, reverse_populate),
    ]
```

## Index Recommandés

```python
# Recherche fréquente par statut
models.Index(fields=['status'])

# Tri chronologique
models.Index(fields=['-created_at'])

# Recherche combinée
models.Index(fields=['owner', 'status'])

# Full-text search PostgreSQL
from django.contrib.postgres.indexes import GinIndex
GinIndex(fields=['name', 'description'], name='{model}_fts_idx')
```

## Contraintes Utiles

```python
# Unicité conditionnelle
models.UniqueConstraint(
    fields=['owner', 'slug'],
    condition=models.Q(is_active=True),
    name='unique_active_{model}_slug'
)

# Check constraint
models.CheckConstraint(
    check=models.Q(status__in=['DRAFT', 'PUBLISHED']),
    name='valid_{model}_status'
)
```
