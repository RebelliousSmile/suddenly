# Tâche 04 : App Federation

**Durée estimée** : 30 min
**Phase** : 1 - Fondations
**Statut** : [ ] À faire
**Dépend de** : 02-app-core

---

## Objectif

Créer l'app `federation` avec les modèles de base `FederatedServer` et `Follow`. Ces modèles sont des structures pour la Phase 4 — la logique de fédération viendra plus tard.

## Prérequis

- Tâche 02 complétée (BaseModel)

## Fichiers à Créer

```
apps/federation/
├── __init__.py
├── apps.py
├── models.py          # FederatedServer, Follow
└── admin.py           # Admin basique
```

## Étapes

### 1. Créer la structure

```bash
mkdir -p apps/federation
touch apps/federation/__init__.py
```

### 2. Créer apps/federation/apps.py

```python
"""Federation app configuration."""
from django.apps import AppConfig


class FederationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.federation'
    verbose_name = 'Fédération'
```

### 3. Créer apps/federation/models.py

```python
"""
Modèles de fédération ActivityPub.

Ces modèles sont des structures de base.
L'implémentation complète viendra en Phase 4.
"""
from django.db import models

from apps.core.models import BaseModel


class ServerStatus(models.TextChoices):
    """Statut d'une instance fédérée."""
    UNKNOWN = 'UNKNOWN', 'Inconnu'
    FEDERATED = 'FEDERATED', 'Fédéré'
    BLOCKED = 'BLOCKED', 'Bloqué'


class FederatedServer(BaseModel):
    """
    Instance fédérée connue.

    Stocke les informations sur les autres instances
    du réseau fédéré.
    """

    server_name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Nom de domaine de l'instance"
    )

    # Infos serveur (via NodeInfo)
    application_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Type d'application (suddenly, mastodon, etc.)"
    )
    application_version = models.CharField(
        max_length=50,
        blank=True,
        help_text="Version de l'application"
    )

    # Statut
    status = models.CharField(
        max_length=20,
        choices=ServerStatus.choices,
        default=ServerStatus.UNKNOWN
    )

    # Stats
    user_count = models.IntegerField(
        default=0,
        help_text="Nombre d'utilisateurs (via NodeInfo)"
    )
    last_checked = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Dernière vérification NodeInfo"
    )

    class Meta:
        db_table = 'federation_federatedserver'
        verbose_name = 'Instance fédérée'
        verbose_name_plural = 'Instances fédérées'
        indexes = [
            models.Index(fields=['server_name']),
            models.Index(fields=['status']),
            models.Index(fields=['application_type']),
        ]

    def __str__(self) -> str:
        return self.server_name

    def is_suddenly_instance(self) -> bool:
        """Retourne True si c'est une instance Suddenly."""
        return self.application_type == 'suddenly'


class FollowTargetType(models.TextChoices):
    """Type de cible pour un follow."""
    USER = 'USER', 'Utilisateur'
    CHARACTER = 'CHARACTER', 'Personnage'
    GAME = 'GAME', 'Partie'


class FollowStatus(models.TextChoices):
    """Statut d'un follow."""
    PENDING = 'PENDING', 'En attente'
    ACCEPTED = 'ACCEPTED', 'Accepté'
    REJECTED = 'REJECTED', 'Refusé'


class Follow(BaseModel):
    """
    Abonnement (User suit User/Character/Game).

    Gère les follows locaux et distants.
    Utilise un pattern polymorphique pour les différents types de cibles.
    """

    follower = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='following_set',
        help_text="L'utilisateur qui suit"
    )

    # Cible polymorphique (local)
    target_type = models.CharField(
        max_length=20,
        choices=FollowTargetType.choices
    )
    target_id = models.UUIDField(
        help_text="UUID de la cible (User, Character, ou Game)"
    )

    # Pour les follows distants
    target_ap_id = models.URLField(
        null=True,
        blank=True,
        help_text="AP ID de la cible (si distante)"
    )

    # Statut
    status = models.CharField(
        max_length=20,
        choices=FollowStatus.choices,
        default=FollowStatus.PENDING
    )

    class Meta:
        db_table = 'federation_follow'
        verbose_name = 'Abonnement'
        verbose_name_plural = 'Abonnements'
        unique_together = [['follower', 'target_type', 'target_id']]
        indexes = [
            models.Index(fields=['follower']),
            models.Index(fields=['target_type', 'target_id']),
            models.Index(fields=['status']),
        ]

    def __str__(self) -> str:
        return f"{self.follower} → {self.target_type}:{self.target_id}"
```

### 4. Créer apps/federation/admin.py

```python
"""Admin configuration for federation."""
from django.contrib import admin

from .models import FederatedServer, Follow


@admin.register(FederatedServer)
class FederatedServerAdmin(admin.ModelAdmin):
    """Admin pour FederatedServer."""

    list_display = [
        'server_name',
        'application_type',
        'status',
        'user_count',
        'last_checked',
    ]
    list_filter = ['status', 'application_type']
    search_fields = ['server_name']
    ordering = ['server_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    """Admin pour Follow."""

    list_display = [
        'follower',
        'target_type',
        'target_id',
        'status',
        'created_at',
    ]
    list_filter = ['status', 'target_type']
    search_fields = ['follower__username']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
```

### 5. Créer apps/federation/__init__.py

```python
"""Federation application."""
default_app_config = 'apps.federation.apps.FederationConfig'
```

## Validation

- [ ] `python -c "from apps.federation.models import FederatedServer, Follow"` fonctionne
- [ ] Modèles sont concrets (pas abstraits)
- [ ] Enums correctement définis

## Notes

- Ces modèles sont des **structures de base**
- La logique ActivityPub (inbox, outbox, signatures) viendra en Phase 4
- Le modèle `Follow` utilise un pattern polymorphique simple (target_type + target_id)

## Références

- `documentation/models/README.md` — Spécifications FederatedServer et Follow
- `documentation/api/activitypub.md` — Activité Follow
