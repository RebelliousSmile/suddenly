# Tâche 08 : App Characters

**Durée estimée** : 3h
**Phase** : 2 - Personnages
**Statut** : [ ] À faire
**Dépend de** : 05-app-games, 07-premiere-migration

---

## Objectif

Créer l'app `characters` avec les modèles `Character` et `CharacterAppearance`, les vues HTMX de liste et de détail, ainsi que les endpoints de recherche et de suggestion de personnages.

User stories couvertes :

- **Mentionner des personnages dans un compte-rendu** — sélecteur de personnages avec création à la volée lors de la rédaction
- **Voir les suggestions de personnages** — recherche PostgreSQL FTS sur `name` et `description` lors de la frappe
- **Voir la fiche d'un personnage avec historique** — page détail avec liste d'apparitions dans les comptes-rendus
- **Rechercher des personnages par nom / système de jeu** — liste filtrée avec FTS et filtre par `game_system`

## Prérequis

- Tâche 05 complétée (Game, Report, ReportCast existent)
- Tâche 07 complétée (migrations initiales appliquées)

## Fichiers à Créer

```
apps/characters/
├── __init__.py
├── apps.py
├── models.py          # Character, CharacterAppearance
├── admin.py
├── views.py           # Liste, détail, HTMX search/suggest
├── urls.py
└── forms.py

templates/characters/
├── list.html          # Page liste avec recherche
├── detail.html        # Fiche personnage + historique
├── _card.html         # Partial carte personnage
├── _search_results.html  # Partial résultats recherche HTMX
└── _suggest.html      # Partial suggestions inline HTMX
```

## Étapes

### 1. Créer la structure

```bash
mkdir -p apps/characters
touch apps/characters/__init__.py
```

### 2. Créer apps/characters/apps.py

```python
"""Characters app configuration."""
from django.apps import AppConfig


class CharactersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.characters'
    verbose_name = 'Personnages'
```

### 3. Créer apps/characters/models.py

```python
"""
Modèles pour les personnages et leurs apparitions.

Character est un acteur ActivityPub de type Person.
CharacterAppearance lie un personnage à un compte-rendu publié.
"""
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from apps.core.models import BaseModel
from apps.core.mixins import ActivityPubMixin


class CharacterStatus(models.TextChoices):
    """Statut d'un personnage dans le réseau de fiction."""
    NPC = 'NPC', 'PNJ'
    PC = 'PC', 'PJ'
    CLAIMED = 'CLAIMED', 'Réclamé'
    ADOPTED = 'ADOPTED', 'Adopté'
    FORKED = 'FORKED', 'Dérivé'


class Character(BaseModel, ActivityPubMixin):
    """
    Personnage (PJ ou PNJ) - acteur ActivityPub de type Person.

    Un Character est créé par un joueur dans le contexte d'une partie
    (origin_game). Il peut être réclamé, adopté ou dérivé par d'autres
    joueurs via le système de liens (voir LinkRequest, CharacterLink).
    """

    # Identité
    name = models.CharField(
        max_length=255,
        help_text="Nom du personnage"
    )
    slug = models.SlugField(
        max_length=255,
        help_text="Slug pour l'URL"
    )
    description = models.TextField(
        blank=True,
        help_text="Description du personnage"
    )
    avatar = models.ImageField(
        upload_to='characters/',
        null=True,
        blank=True,
        help_text="Avatar du personnage"
    )

    # Statut
    status = models.CharField(
        max_length=20,
        choices=CharacterStatus.choices,
        default=CharacterStatus.NPC,
        help_text="Statut narratif du personnage"
    )

    # Relations utilisateurs
    owner = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='characters',
        help_text="Joueur qui possède le personnage (null pour PNJ)"
    )
    creator = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='created_characters',
        help_text="Joueur qui a créé le personnage"
    )

    # Origine
    origin_game = models.ForeignKey(
        'games.Game',
        on_delete=models.CASCADE,
        related_name='characters',
        help_text="Partie dans laquelle le personnage est apparu"
    )

    # Lien parent (pour Fork)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='forks',
        help_text="Personnage source (pour Fork uniquement)"
    )

    # Lien externe vers fiche technique
    sheet_url = models.URLField(
        blank=True,
        help_text="URL de la fiche de personnage (système externe)"
    )

    class Meta:
        db_table = 'characters_character'
        verbose_name = 'Personnage'
        verbose_name_plural = 'Personnages'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['owner']),
            models.Index(fields=['creator']),
            models.Index(fields=['origin_game']),
            models.Index(fields=['ap_id']),
            models.Index(fields=['local', 'status']),
        ]

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse('characters:detail', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def is_available(self) -> bool:
        """Retourne True si le personnage peut être réclamé/adopté/dérivé."""
        return self.status == CharacterStatus.NPC

    def can_be_claimed_by(self, user) -> bool:
        """Retourne True si l'utilisateur peut initier une demande de lien."""
        if not user.is_authenticated:
            return False
        if self.creator == user:
            return False
        return self.is_available()


class AppearanceRole(models.TextChoices):
    """Rôle d'un personnage dans un compte-rendu."""
    MAIN = 'MAIN', 'Principal'
    SUPPORTING = 'SUPPORTING', 'Secondaire'
    MENTIONED = 'MENTIONED', 'Mentionné'


class CharacterAppearance(BaseModel):
    """
    Apparition d'un personnage dans un compte-rendu publié.

    Créée lors de la publication d'un Report, à partir du ReportCast
    (brouillon) ou directement via le sélecteur de personnages.
    """

    character = models.ForeignKey(
        'Character',
        on_delete=models.CASCADE,
        related_name='appearances',
        help_text="Personnage apparu dans ce compte-rendu"
    )
    report = models.ForeignKey(
        'games.Report',
        on_delete=models.CASCADE,
        related_name='appearances',
        help_text="Compte-rendu dans lequel le personnage apparaît"
    )

    role = models.CharField(
        max_length=20,
        choices=AppearanceRole.choices,
        default=AppearanceRole.MENTIONED,
        help_text="Rôle du personnage dans ce compte-rendu"
    )
    context = models.TextField(
        blank=True,
        help_text="Description du rôle dans cette scène"
    )

    class Meta:
        db_table = 'characters_characterappearance'
        verbose_name = 'Apparition'
        verbose_name_plural = 'Apparitions'
        unique_together = [['character', 'report']]
        ordering = ['-report__published_at']
        indexes = [
            models.Index(fields=['character']),
            models.Index(fields=['report']),
        ]

    def __str__(self) -> str:
        return f"{self.character.name} dans {self.report}"
```

**Points clés** :
- `Character` hérite de `BaseModel` et `ActivityPubMixin` (acteur AP de type `Person`)
- `owner` est nullable : un PNJ (`NPC`) n'a pas de propriétaire
- `creator` est obligatoire et non nullable : toujours traçable
- `parent` est une auto-référence pour le workflow Fork
- `CharacterAppearance` enregistre les apparitions post-publication (pas le brouillon — c'est `ReportCast` dans `games`)
- La contrainte `unique_together = [['character', 'report']]` empêche les doublons

### 4. Créer apps/characters/admin.py

```python
"""Admin configuration for characters."""
from django.contrib import admin

from .models import Character, CharacterAppearance, CharacterStatus


class CharacterAppearanceInline(admin.TabularInline):
    """Inline des apparitions dans la fiche personnage."""
    model = CharacterAppearance
    extra = 0
    fields = ['report', 'role', 'context']
    readonly_fields = ['report']
    show_change_link = True


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    """Admin pour Character."""

    list_display = ['name', 'status', 'creator', 'owner', 'origin_game', 'local', 'created_at']
    list_filter = ['status', 'local', 'origin_game__game_system']
    search_fields = ['name', 'description', 'creator__username', 'owner__username']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'ap_id']
    inlines = [CharacterAppearanceInline]

    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'status', 'avatar')
        }),
        ('Description', {
            'fields': ('description', 'sheet_url')
        }),
        ('Relations', {
            'fields': ('creator', 'owner', 'origin_game', 'parent')
        }),
        ('Fédération', {
            'fields': ('local', 'ap_id', 'inbox', 'outbox'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CharacterAppearance)
class CharacterAppearanceAdmin(admin.ModelAdmin):
    """Admin pour CharacterAppearance."""

    list_display = ['character', 'report', 'role', 'created_at']
    list_filter = ['role']
    search_fields = ['character__name', 'report__title']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
```

### 5. Créer apps/characters/views.py

Les vues couvrent deux besoins distincts : la navigation (liste, détail) et les interactions HTMX (recherche, suggestions inline pour le sélecteur de personnages dans les comptes-rendus).

```python
"""Views for characters app."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.db.models import Prefetch, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView, ListView

from apps.games.models import Report, ReportStatus
from .models import Character, CharacterAppearance, CharacterStatus


class CharacterListView(ListView):
    """Liste des personnages avec recherche et filtres."""

    model = Character
    template_name = 'characters/list.html'
    context_object_name = 'characters'
    paginate_by = 24

    def get_queryset(self):
        qs = (
            Character.objects
            .filter(local=True)
            .select_related('creator', 'owner', 'origin_game')
            .order_by('-created_at')
        )

        # Filtre par statut
        status = self.request.GET.get('status')
        if status in CharacterStatus.values:
            qs = qs.filter(status=status)

        # Filtre par système de jeu
        game_system = self.request.GET.get('game_system', '').strip()
        if game_system:
            qs = qs.filter(origin_game__game_system__icontains=game_system)

        # Recherche plein texte (PostgreSQL FTS)
        q = self.request.GET.get('q', '').strip()
        if q:
            search_query = SearchQuery(q, config='french')
            search_vector = SearchVector('name', weight='A', config='french') + \
                            SearchVector('description', weight='B', config='french')
            qs = (
                qs
                .annotate(rank=SearchRank(search_vector, search_query))
                .filter(rank__gt=0.01)
                .order_by('-rank')
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['game_system_filter'] = self.request.GET.get('game_system', '')
        context['character_statuses'] = CharacterStatus.choices
        return context


class CharacterDetailView(DetailView):
    """Fiche d'un personnage avec historique d'apparitions."""

    model = Character
    template_name = 'characters/detail.html'
    context_object_name = 'character'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return (
            Character.objects
            .select_related('creator', 'owner', 'origin_game', 'parent')
            .prefetch_related(
                Prefetch(
                    'appearances',
                    queryset=(
                        CharacterAppearance.objects
                        .select_related('report', 'report__game', 'report__author')
                        .filter(report__status=ReportStatus.PUBLISHED)
                        .order_by('-report__published_at')
                    )
                ),
                Prefetch(
                    'quotes',
                    queryset=__import__(
                        'apps.quotes.models', fromlist=['Quote']
                    ).Quote.objects.filter(visibility='PUBLIC').order_by('-created_at')
                ),
                'forks',
                'links_as_source',
                'links_as_target',
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['can_claim'] = self.object.can_be_claimed_by(user)
        return context
```

**Endpoint HTMX — suggestions inline** (sélecteur de personnages dans un compte-rendu) :

```python
@require_http_methods(["GET"])
def htmx_character_suggest(request):
    """
    Suggestions de personnages pendant la rédaction d'un compte-rendu.

    Utilisé par le sélecteur HTMX du formulaire ReportForm.
    Retourne un partial '_suggest.html' avec jusqu'à 5 suggestions.

    Paramètres GET :
        q        — Terme de recherche (nom du personnage)
        game_id  — Optionnel, limite aux personnages de la partie en cours
    """
    q = request.GET.get('q', '').strip()
    game_id = request.GET.get('game_id', '')

    if len(q) < 2:
        return HttpResponse('')

    qs = (
        Character.objects
        .filter(local=True)
        .select_related('origin_game')
        .order_by('name')
    )

    if game_id:
        qs = qs.filter(Q(origin_game_id=game_id) | Q(name__icontains=q))

    # Recherche FTS prioritaire, fallback icontains
    search_query = SearchQuery(q, config='french')
    search_vector = SearchVector('name', config='french')
    qs = (
        qs
        .annotate(rank=SearchRank(search_vector, search_query))
        .filter(Q(rank__gt=0.01) | Q(name__icontains=q))
        .order_by('-rank', 'name')[:5]
    )

    return render(request, 'characters/_suggest.html', {
        'suggestions': qs,
        'query': q,
    })


@require_http_methods(["GET"])
def htmx_character_search(request):
    """
    Recherche de personnages via HTMX (liste filtrée, partial).

    Retourne '_search_results.html' pour mise à jour HTMX de la liste.
    """
    q = request.GET.get('q', '').strip()
    game_system = request.GET.get('game_system', '').strip()
    status = request.GET.get('status', '').strip()

    qs = (
        Character.objects
        .filter(local=True)
        .select_related('creator', 'owner', 'origin_game')
    )

    if status in CharacterStatus.values:
        qs = qs.filter(status=status)

    if game_system:
        qs = qs.filter(origin_game__game_system__icontains=game_system)

    if q:
        search_query = SearchQuery(q, config='french')
        search_vector = (
            SearchVector('name', weight='A', config='french') +
            SearchVector('description', weight='B', config='french')
        )
        qs = (
            qs
            .annotate(rank=SearchRank(search_vector, search_query))
            .filter(rank__gt=0.01)
            .order_by('-rank')
        )
    else:
        qs = qs.order_by('-created_at')

    return render(request, 'characters/_search_results.html', {
        'characters': qs[:24],
        'query': q,
    })
```

**Points clés des vues** :
- `CharacterListView` gère la recherche FTS et les filtres par status/game_system dans un seul queryset
- `CharacterDetailView` précharge les apparitions avec les reports publiés uniquement (pas les brouillons)
- `htmx_character_suggest` est l'endpoint pour le sélecteur inline pendant la rédaction (paramètre `game_id` optionnel pour limiter au contexte de la partie)
- `htmx_character_search` est l'endpoint pour la mise à jour de la liste côté page de recherche

### 6. Créer apps/characters/urls.py

```python
"""URL configuration for characters app."""
from django.urls import path

from . import views

app_name = 'characters'

urlpatterns = [
    # Liste et recherche
    path('characters/', views.CharacterListView.as_view(), name='list'),

    # Détail
    path('characters/<slug:slug>/', views.CharacterDetailView.as_view(), name='detail'),

    # Endpoints HTMX
    path('htmx/characters/suggest/', views.htmx_character_suggest, name='htmx_suggest'),
    path('htmx/characters/search/', views.htmx_character_search, name='htmx_search'),
]
```

### 7. Créer apps/characters/forms.py

```python
"""Forms for characters app."""
from django import forms

from .models import Character, CharacterAppearance, AppearanceRole


class CharacterQuickCreateForm(forms.ModelForm):
    """
    Formulaire de création rapide d'un PNJ à la volée.

    Utilisé dans le sélecteur de personnages pendant la rédaction
    d'un compte-rendu, quand le personnage n'existe pas encore.
    """

    class Meta:
        model = Character
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        if len(name) < 2:
            raise forms.ValidationError("Le nom doit faire au moins 2 caractères.")
        return name


class CharacterAppearanceForm(forms.ModelForm):
    """Formulaire d'ajout d'une apparition à un compte-rendu."""

    class Meta:
        model = CharacterAppearance
        fields = ['character', 'role', 'context']
        widgets = {
            'context': forms.Textarea(attrs={'rows': 2}),
        }
```

### 8. Créer apps/characters/__init__.py

```python
"""Characters application."""
default_app_config = 'apps.characters.apps.CharactersConfig'
```

### 9. Enregistrer l'app dans les settings

Dans `config/settings/base.py`, ajouter `apps.characters` à `INSTALLED_APPS` :

```python
INSTALLED_APPS = [
    # ...
    'apps.games',
    'apps.characters',   # ← ajouter ici
    # ...
]
```

### 10. Enregistrer les URLs

Dans `config/urls.py`, inclure les URLs de l'app :

```python
from django.urls import include, path

urlpatterns = [
    # ...
    path('', include('apps.characters.urls')),
]
```

### 11. Ajouter l'index FTS en migration SQL

Créer une migration vide pour ajouter l'index GIN PostgreSQL :

```bash
python manage.py makemigrations characters --empty --name add_character_fts_index
```

Dans le fichier généré :

```python
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('characters', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS idx_character_fts
                ON characters_character
                USING gin(
                    to_tsvector('french', name || ' ' || coalesce(description, ''))
                );
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_character_fts;",
        ),
    ]
```

## Validation

- [ ] Modèles `Character` et `CharacterAppearance` importables
- [ ] FK vers `users.User`, `games.Game`, `games.Report` fonctionnelles
- [ ] Slug auto-généré depuis `name`
- [ ] Admin accessible avec inline d'apparitions
- [ ] `CharacterListView` filtre par `status` et `game_system`
- [ ] Recherche FTS opérationnelle (PostgreSQL requis)
- [ ] `htmx_character_suggest` retourne des résultats pour une requête de 2 caractères minimum
- [ ] `htmx_character_search` retourne un partial utilisable par HTMX
- [ ] `CharacterDetailView` ne charge que les apparitions de reports `PUBLISHED`
- [ ] Index GIN créé en base

## Notes

- `CharacterAppearance` est distincte de `ReportCast` : `ReportCast` est le brouillon (dans `games`), `CharacterAppearance` est la liaison définitive créée à la publication du report
- La FK `quotes` dans `CharacterDetailView` est importée dynamiquement pour éviter un import circulaire (`characters` ← `quotes`) ; dans la pratique, préférer un `prefetch_related` déclaré après que l'app `quotes` est disponible, ou centraliser dans un service
- Les modèles `LinkRequest`, `CharacterLink` et `SharedSequence` (workflow Claim/Adopt/Fork) sont définis dans cette même app `characters` mais couverts par la tâche suivante (Phase 3 — Liens)
- Les templates seront créés dans la tâche 06 (templates de base) ou en parallèle de cette tâche

## Références

- `docs/models/README.md` — Character, CharacterAppearance, contraintes SQL et index FTS
- `docs/memory-bank/user-stories.md` — Domaine 4 (Personnages) et Domaine 3 (Comptes-rendus, suggestions)
- `docs/memory-bank/CODEBASE_STRUCTURE.md` — `apps/characters/services.py` comme module critique pour Phase 3
