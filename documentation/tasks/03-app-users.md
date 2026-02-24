# Tâche 03 : App Users

**Durée estimée** : 2h
**Phase** : 1 - Fondations
**Statut** : [ ] À faire
**Dépend de** : 02-app-core, 04-app-federation

---

## Objectif

Créer l'app `users` avec le modèle User étendu, l'intégration allauth, et les vues de profil.

## Prérequis

- Tâche 02 complétée (BaseModel, ActivityPubMixin)
- Tâche 04 au moins commencée (FederatedServer existe)

## Fichiers à Créer

```
apps/users/
├── __init__.py
├── apps.py
├── models.py          # User étendu
├── admin.py           # Admin personnalisé
├── views.py           # ProfileView
├── urls.py            # Routes /@username
└── forms.py           # ProfileForm
```

## Étapes

### 1. Créer la structure

```bash
mkdir -p apps/users
touch apps/users/__init__.py
```

### 2. Créer apps/users/apps.py

```python
"""Users app configuration."""
from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    verbose_name = 'Utilisateurs'
```

### 3. Créer apps/users/models.py

```python
"""
Modèle User étendu.

User est un acteur ActivityPub de type Person.
"""
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse

from apps.core.mixins import ActivityPubMixin


class User(AbstractUser, ActivityPubMixin):
    """
    Utilisateur/Joueur - acteur ActivityPub principal.

    Hérite de AbstractUser pour l'authentification Django
    et de ActivityPubMixin pour la fédération.
    """

    # Override id to use UUID
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Identité publique
    display_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Nom affiché (différent du username)"
    )
    bio = models.TextField(
        blank=True,
        help_text="Biographie publique"
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True
    )

    # Email obligatoire
    email = models.EmailField(unique=True)

    # Fédération
    federated_server = models.ForeignKey(
        'federation.FederatedServer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text="Instance d'origine (null si local)"
    )
    shared_inbox = models.URLField(
        null=True,
        blank=True,
        help_text="Shared inbox de l'instance"
    )

    # Préférences de langue
    preferred_languages = models.JSONField(
        default=list,
        blank=True,
        help_text="Langues acceptées pour le feed (codes ISO 639-1)"
    )
    content_language = models.CharField(
        max_length=10,
        default='fr',
        help_text="Langue par défaut des publications"
    )
    show_unlabeled_content = models.BooleanField(
        default=True,
        help_text="Afficher les contenus sans langue définie"
    )

    # Timestamps (AbstractUser a date_joined, on ajoute updated_at)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users_user'
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['email']),
            models.Index(fields=['ap_id']),
            models.Index(fields=['local']),
        ]

    def __str__(self) -> str:
        return self.display_name or self.username

    def get_absolute_url(self) -> str:
        return reverse('users:profile', kwargs={'username': self.username})

    def get_display_name(self) -> str:
        """Retourne le nom à afficher."""
        return self.display_name or self.username

    def save(self, *args, **kwargs):
        # Initialiser preferred_languages si vide
        if not self.preferred_languages:
            self.preferred_languages = [self.content_language]
        super().save(*args, **kwargs)
```

### 4. Créer apps/users/admin.py

```python
"""Admin configuration for User."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin personnalisé pour User."""

    list_display = [
        'username',
        'email',
        'display_name',
        'local',
        'is_active',
        'date_joined',
    ]
    list_filter = [
        'is_active',
        'is_staff',
        'local',
        'content_language',
    ]
    search_fields = ['username', 'email', 'display_name']
    ordering = ['-date_joined']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profil Public', {
            'fields': ('display_name', 'bio', 'avatar'),
        }),
        ('Fédération', {
            'fields': ('local', 'ap_id', 'federated_server'),
            'classes': ('collapse',),
        }),
        ('Préférences', {
            'fields': ('content_language', 'preferred_languages', 'show_unlabeled_content'),
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Profil', {
            'fields': ('email', 'display_name'),
        }),
    )
```

### 5. Créer apps/users/views.py

```python
"""Views for users app."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, UpdateView
from django.urls import reverse_lazy

from .models import User
from .forms import ProfileForm


class ProfileView(DetailView):
    """Vue du profil utilisateur."""

    model = User
    template_name = 'users/profile.html'
    context_object_name = 'profile_user'
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_queryset(self):
        return User.objects.filter(is_active=True)


class ProfileEditView(LoginRequiredMixin, UpdateView):
    """Édition du profil."""

    model = User
    form_class = ProfileForm
    template_name = 'users/profile_edit.html'
    success_url = reverse_lazy('users:profile')

    def get_object(self):
        return self.request.user

    def get_success_url(self):
        return reverse_lazy('users:profile', kwargs={'username': self.request.user.username})
```

### 6. Créer apps/users/urls.py

```python
"""URL configuration for users app."""
from django.urls import path

from . import views

app_name = 'users'

urlpatterns = [
    path('<str:username>/', views.ProfileView.as_view(), name='profile'),
    path('<str:username>/edit/', views.ProfileEditView.as_view(), name='profile_edit'),
]
```

### 7. Créer apps/users/forms.py

```python
"""Forms for users app."""
from django import forms

from .models import User


class ProfileForm(forms.ModelForm):
    """Formulaire d'édition du profil."""

    class Meta:
        model = User
        fields = [
            'display_name',
            'bio',
            'avatar',
            'content_language',
            'preferred_languages',
            'show_unlabeled_content',
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
            'preferred_languages': forms.TextInput(attrs={
                'placeholder': 'fr, en, de...'
            }),
        }

    def clean_preferred_languages(self):
        """Convertit la chaîne en liste."""
        value = self.cleaned_data.get('preferred_languages')
        if isinstance(value, str):
            return [lang.strip() for lang in value.split(',') if lang.strip()]
        return value or []
```

### 8. Créer apps/users/__init__.py

```python
"""Users application."""
default_app_config = 'apps.users.apps.UsersConfig'
```

## Validation

- [ ] `python manage.py check` passe (après création de federation)
- [ ] Modèle User importable
- [ ] Admin accessible après migration
- [ ] Vue de profil fonctionne

## Notes

- **IMPORTANT** : Cette tâche dépend de `federation.FederatedServer`
- Créer la tâche 04 d'abord ou commenter temporairement la FK `federated_server`
- Les templates seront créés dans la tâche 06

## Références

- `documentation/models/README.md` — Spécification User
- `documentation/api/activitypub.md` — User comme Person AP
