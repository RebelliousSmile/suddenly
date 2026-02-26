# Tâche 05 : App Games

**Durée estimée** : 2h
**Phase** : 1 - Fondations
**Statut** : [ ] À faire
**Dépend de** : 03-app-users

---

## Objectif

Créer l'app `games` avec les modèles Game, Report, ReportCast et les vues HTMX de base.

## Prérequis

- Tâche 03 complétée (User existe)
- Tâche 04 complétée (FederatedServer existe)

## Fichiers à Créer

```
apps/games/
├── __init__.py
├── apps.py
├── models.py          # Game, Report, ReportCast
├── admin.py
├── views.py           # CRUD + HTMX
├── urls.py
└── forms.py
```

## Étapes

### 1. Créer la structure

```bash
mkdir -p apps/games
touch apps/games/__init__.py
```

### 2. Créer apps/games/apps.py

```python
"""Games app configuration."""
from django.apps import AppConfig


class GamesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.games'
    verbose_name = 'Parties'
```

### 3. Créer apps/games/models.py

```python
"""
Modèles pour les parties et comptes-rendus.

Game est un acteur ActivityPub de type Group.
Report est un objet ActivityPub de type Article.
"""
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from apps.core.models import BaseModel
from apps.core.mixins import ActivityPubMixin


class Game(BaseModel, ActivityPubMixin):
    """
    Partie/Campagne - acteur ActivityPub de type Group.

    Une Game contient des Reports et est suivable.
    """

    # Identité
    title = models.CharField(
        max_length=255,
        help_text="Titre de la partie/campagne"
    )
    slug = models.SlugField(
        max_length=255,
        help_text="Slug pour l'URL"
    )
    description = models.TextField(
        blank=True,
        help_text="Description de la partie"
    )
    game_system = models.CharField(
        max_length=100,
        blank=True,
        help_text="Système de jeu (City of Mist, D&D, etc.)"
    )

    # Propriétaire
    owner = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='games',
        help_text="Propriétaire de la partie"
    )

    # Visibilité
    is_public = models.BooleanField(
        default=True,
        help_text="Visible publiquement"
    )

    class Meta:
        db_table = 'games_game'
        verbose_name = 'Partie'
        verbose_name_plural = 'Parties'
        unique_together = [['owner', 'slug']]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'is_public']),
            models.Index(fields=['game_system']),
            models.Index(fields=['ap_id']),
            models.Index(fields=['local']),
        ]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse('games:game_detail', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_published_reports(self):
        """Retourne les reports publiés."""
        return self.reports.filter(status=ReportStatus.PUBLISHED).order_by('-published_at')


class ReportStatus(models.TextChoices):
    """Statut d'un compte-rendu."""
    DRAFT = 'DRAFT', 'Brouillon'
    PUBLISHED = 'PUBLISHED', 'Publié'


class Report(BaseModel, ActivityPubMixin):
    """
    Compte-rendu de partie - objet ActivityPub de type Article.
    """

    # Contenu
    title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Titre du compte-rendu"
    )
    slug = models.SlugField(
        max_length=255,
        help_text="Slug pour l'URL"
    )
    content = models.TextField(
        help_text="Contenu en Markdown"
    )
    content_html = models.TextField(
        blank=True,
        help_text="Contenu rendu en HTML (cache)"
    )

    # Relations
    game = models.ForeignKey(
        'Game',
        on_delete=models.CASCADE,
        related_name='reports'
    )
    author = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='reports'
    )

    # Statut
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.DRAFT
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Langue
    language = models.CharField(
        max_length=10,
        blank=True,
        help_text="Code langue ISO 639-1 (fr, en, de...)"
    )

    class Meta:
        db_table = 'games_report'
        verbose_name = 'Compte-rendu'
        verbose_name_plural = 'Comptes-rendus'
        unique_together = [['game', 'slug']]
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['game', 'status']),
            models.Index(fields=['author']),
            models.Index(fields=['published_at']),
            models.Index(fields=['ap_id']),
            models.Index(fields=['language']),
        ]

    def __str__(self) -> str:
        return self.title or f"Report #{self.id}"

    def get_absolute_url(self) -> str:
        return reverse('games:report_detail', kwargs={
            'game_slug': self.game.slug,
            'slug': self.slug
        })

    def save(self, *args, **kwargs):
        # Générer le slug si absent
        if not self.slug:
            base = self.title or str(self.id)[:8]
            self.slug = slugify(base)

        # Rendre le Markdown en HTML
        if self.content:
            import markdown
            import bleach
            # Rendu Markdown
            html = markdown.markdown(self.content, extensions=['extra', 'nl2br'])
            # Sanitization
            allowed_tags = [
                'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                'strong', 'em', 'a', 'ul', 'ol', 'li',
                'blockquote', 'code', 'pre', 'br', 'hr'
            ]
            self.content_html = bleach.clean(html, tags=allowed_tags, strip=True)

        # Définir published_at si publication
        if self.status == ReportStatus.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()

        # Hériter la langue de l'auteur si non définie
        if not self.language and self.author_id:
            self.language = self.author.content_language

        super().save(*args, **kwargs)

    def publish(self) -> None:
        """Publie le compte-rendu."""
        self.status = ReportStatus.PUBLISHED
        self.published_at = timezone.now()
        self.save(update_fields=['status', 'published_at', 'updated_at'])

    def is_draft(self) -> bool:
        return self.status == ReportStatus.DRAFT

    def is_published(self) -> bool:
        return self.status == ReportStatus.PUBLISHED


class ReportCast(BaseModel):
    """
    Distribution prévue pour un brouillon.

    Permet de préparer les personnages qui apparaîtront
    dans le compte-rendu avant sa publication.
    """

    report = models.ForeignKey(
        'Report',
        on_delete=models.CASCADE,
        related_name='cast'
    )

    # Soit personnage existant...
    character = models.ForeignKey(
        'characters.Character',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Personnage existant"
    )

    # ...soit nouveau PNJ à créer
    new_character_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Nom du nouveau PNJ à créer"
    )
    new_character_description = models.TextField(
        blank=True,
        help_text="Description du nouveau PNJ"
    )

    # Rôle
    role = models.CharField(
        max_length=20,
        default='MENTIONED',
        help_text="Rôle dans le compte-rendu (MAIN, SUPPORTING, MENTIONED)"
    )

    class Meta:
        db_table = 'games_reportcast'
        verbose_name = 'Distribution'
        verbose_name_plural = 'Distributions'
        indexes = [
            models.Index(fields=['report']),
        ]

    def __str__(self) -> str:
        if self.character:
            return f"{self.character.name} in {self.report}"
        return f"{self.new_character_name} (new) in {self.report}"
```

### 4. Créer apps/games/admin.py

```python
"""Admin configuration for games."""
from django.contrib import admin

from .models import Game, Report, ReportCast


class ReportInline(admin.TabularInline):
    """Inline pour les reports dans Game."""
    model = Report
    extra = 0
    fields = ['title', 'status', 'published_at']
    readonly_fields = ['published_at']
    show_change_link = True


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    """Admin pour Game."""

    list_display = ['title', 'owner', 'game_system', 'is_public', 'local', 'created_at']
    list_filter = ['is_public', 'local', 'game_system']
    search_fields = ['title', 'description', 'owner__username']
    prepopulated_fields = {'slug': ('title',)}
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'ap_id']
    inlines = [ReportInline]


class ReportCastInline(admin.TabularInline):
    """Inline pour le cast dans Report."""
    model = ReportCast
    extra = 1
    fields = ['character', 'new_character_name', 'role']


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """Admin pour Report."""

    list_display = ['title', 'game', 'author', 'status', 'language', 'published_at']
    list_filter = ['status', 'language', 'game']
    search_fields = ['title', 'content', 'author__username']
    prepopulated_fields = {'slug': ('title',)}
    ordering = ['-created_at']
    readonly_fields = ['content_html', 'created_at', 'updated_at', 'ap_id']
    inlines = [ReportCastInline]

    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'game', 'author')
        }),
        ('Contenu', {
            'fields': ('content', 'content_html', 'language')
        }),
        ('Publication', {
            'fields': ('status', 'published_at')
        }),
        ('Fédération', {
            'fields': ('local', 'ap_id'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
```

### 5. Créer apps/games/views.py

```python
"""Views for games app."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404

from .models import Game, Report, ReportStatus
from .forms import GameForm, ReportForm


class HomeView(ListView):
    """Page d'accueil avec les parties publiques."""

    model = Game
    template_name = 'games/home.html'
    context_object_name = 'games'
    paginate_by = 12

    def get_queryset(self):
        return (
            Game.objects
            .filter(is_public=True, local=True)
            .select_related('owner')
            .order_by('-created_at')
        )


class GameDetailView(DetailView):
    """Détail d'une partie."""

    model = Game
    template_name = 'games/game_detail.html'
    context_object_name = 'game'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return Game.objects.select_related('owner')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['reports'] = self.object.get_published_reports()[:10]
        return context


class GameCreateView(LoginRequiredMixin, CreateView):
    """Création d'une partie."""

    model = Game
    form_class = GameForm
    template_name = 'games/game_form.html'

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class GameUpdateView(LoginRequiredMixin, UpdateView):
    """Modification d'une partie."""

    model = Game
    form_class = GameForm
    template_name = 'games/game_form.html'

    def get_queryset(self):
        return Game.objects.filter(owner=self.request.user)


class ReportDetailView(DetailView):
    """Détail d'un compte-rendu."""

    model = Report
    template_name = 'games/report_detail.html'
    context_object_name = 'report'

    def get_queryset(self):
        return (
            Report.objects
            .filter(status=ReportStatus.PUBLISHED)
            .select_related('game', 'author')
        )

    def get_object(self):
        return get_object_or_404(
            self.get_queryset(),
            game__slug=self.kwargs['game_slug'],
            slug=self.kwargs['slug']
        )


class ReportCreateView(LoginRequiredMixin, CreateView):
    """Création d'un compte-rendu."""

    model = Report
    form_class = ReportForm
    template_name = 'games/report_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class ReportUpdateView(LoginRequiredMixin, UpdateView):
    """Modification d'un compte-rendu."""

    model = Report
    form_class = ReportForm
    template_name = 'games/report_form.html'

    def get_queryset(self):
        return Report.objects.filter(author=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
```

### 6. Créer apps/games/urls.py

```python
"""URL configuration for games app."""
from django.urls import path

from . import views

app_name = 'games'

urlpatterns = [
    # Home
    path('', views.HomeView.as_view(), name='home'),

    # Games
    path('games/', views.HomeView.as_view(), name='game_list'),
    path('games/new/', views.GameCreateView.as_view(), name='game_create'),
    path('games/<slug:slug>/', views.GameDetailView.as_view(), name='game_detail'),
    path('games/<slug:slug>/edit/', views.GameUpdateView.as_view(), name='game_update'),

    # Reports
    path('games/<slug:game_slug>/reports/new/', views.ReportCreateView.as_view(), name='report_create'),
    path('games/<slug:game_slug>/<slug:slug>/', views.ReportDetailView.as_view(), name='report_detail'),
    path('games/<slug:game_slug>/<slug:slug>/edit/', views.ReportUpdateView.as_view(), name='report_update'),
]
```

### 7. Créer apps/games/forms.py

```python
"""Forms for games app."""
from django import forms

from .models import Game, Report


class GameForm(forms.ModelForm):
    """Formulaire de création/édition de partie."""

    class Meta:
        model = Game
        fields = ['title', 'description', 'game_system', 'is_public']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class ReportForm(forms.ModelForm):
    """Formulaire de création/édition de compte-rendu."""

    class Meta:
        model = Report
        fields = ['title', 'game', 'content', 'language', 'status']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 15}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Limiter les games à celles de l'utilisateur
        if user:
            self.fields['game'].queryset = Game.objects.filter(owner=user)
```

### 8. Créer apps/games/__init__.py

```python
"""Games application."""
default_app_config = 'apps.games.apps.GamesConfig'
```

## Validation

- [ ] Modèles Game et Report importables
- [ ] FK vers User fonctionne
- [ ] Admin accessible
- [ ] Slug auto-généré
- [ ] Markdown rendu en HTML

## Notes

- ReportCast référence `characters.Character` qui n'existe pas encore
- Commenter temporairement cette FK ou créer l'app characters d'abord
- Les templates seront créés dans la tâche 06

## Références

- `documentation/models/README.md` — Spécifications Game et Report
- `documentation/api/activitypub.md` — Game comme Group, Report comme Article
