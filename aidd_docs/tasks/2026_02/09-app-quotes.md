# Tâche 09 : App Quotes

**Durée estimée** : 2h
**Phase** : 2 - Personnages
**Statut** : [ ] À faire
**Dépend de** : 08-app-characters

---

## Objectif

Créer l'app `quotes` avec le modèle Quote et les vues HTMX permettant d'ajouter une citation depuis la fiche d'un personnage ou depuis un compte-rendu, et d'afficher la liste des citations d'un personnage.

## Prérequis

- Tâche 08 complétée (Character existe)
- Tâche 05 complétée (Report existe)
- Tâche 03 complétée (User existe)

## User Stories Couvertes

**Domaine 5 — Citations** (`docs/memory-bank/user-stories.md`)

### "Ajouter une citation à un personnage"

> En tant que joueur solo, je veux enregistrer une réplique mémorable d'un personnage pendant ou après une session, afin que les moments forts de mes parties soient préservés.

Critères d'acceptation :
- Étant donné : je suis sur la fiche d'un personnage ou dans un compte-rendu
- Quand : j'ajoute une citation avec son contexte
- Alors : la citation apparaît sur la fiche du personnage et est fédérée (si publique)
- Et : je peux choisir entre Éphémère (non fédérée), Privée ou Publique

## Fichiers à Créer

```
apps/quotes/
├── __init__.py
├── apps.py
├── models.py          # Quote, QuoteVisibility
├── admin.py
├── views.py           # Liste + ajout HTMX
├── urls.py
└── forms.py

templates/quotes/
├── _quote_card.html           # Partial : une citation
├── _quote_form.html           # Partial HTMX : formulaire d'ajout
├── _character_quotes.html     # Partial HTMX : liste des citations d'un personnage
└── quote_list.html            # Page complète (optionnelle, citations publiques)
```

## Étapes

### 1. Créer la structure

```bash
mkdir -p apps/quotes
touch apps/quotes/__init__.py
```

### 2. Créer apps/quotes/apps.py

```python
"""Citations app configuration."""
from django.apps import AppConfig


class QuotesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.quotes'
    verbose_name = 'Citations'
```

### 3. Créer apps/quotes/models.py

Le modèle `Quote` est un objet ActivityPub de type `Note`. Il porte une visibilité à trois niveaux :

- `EPHEMERAL` : dialogue passe-partout, non persistant au-delà de la session, non fédéré.
- `PRIVATE` : persisté en base, visible uniquement par l'auteur, non fédéré.
- `PUBLIC` : persisté et fédéré via ActivityPub.

Points clés du modèle :

```python
class QuoteVisibility(models.TextChoices):
    EPHEMERAL = 'EPHEMERAL', 'Éphémère (non fédérée, passe-partout)'
    PRIVATE = 'PRIVATE', 'Privée (non fédérée)'
    PUBLIC = 'PUBLIC', 'Publique (fédérée)'


class Quote(BaseModel, ActivityPubMixin):
    """Citation mémorable d'un personnage — objet ActivityPub de type Note."""

    # Contenu
    content = models.TextField()          # La réplique
    context = models.TextField(blank=True)  # Situation narrative

    # Relations
    character = models.ForeignKey(
        'characters.Character',
        on_delete=models.CASCADE,
        related_name='quotes'
    )
    author = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='quotes'
    )
    report = models.ForeignKey(         # Compte-rendu d'origine (optionnel)
        'games.Report',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='quotes'
    )

    # Visibilité
    visibility = models.CharField(
        max_length=20,
        choices=QuoteVisibility.choices,
        default=QuoteVisibility.PUBLIC
    )

    # Langue ISO 639-1 (fr, en, de...)
    language = models.CharField(
        max_length=10,
        blank=True,
        help_text="Code langue ISO 639-1. Hérité de l'auteur si non défini."
    )

    class Meta:
        db_table = 'quotes_quote'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['character', 'visibility']),
            models.Index(fields=['author']),
            models.Index(fields=['report']),
            models.Index(fields=['ap_id']),
        ]
```

Comportements à implémenter dans `save()` :

- Hériter `language` de `author.content_language` si le champ est vide au moment de la sauvegarde.
- Ne pas renseigner `ap_id` pour les citations `EPHEMERAL` et `PRIVATE` (non fédérées).

### 4. Créer apps/quotes/admin.py

Points clés :

```python
@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ['character', 'author', 'visibility', 'language', 'created_at']
    list_filter = ['visibility', 'language']
    search_fields = ['content', 'context', 'character__name', 'author__username']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'ap_id']
```

### 5. Créer apps/quotes/views.py

Deux endpoints principaux :

**`CharacterQuoteListView`** — Liste des citations publiques d'un personnage (partiel HTMX ou page complète).

```python
class CharacterQuoteListView(DetailView):
    """Citations d'un personnage. Répond en partial si requête HTMX."""

    model = Character  # importé depuis apps.characters.models
    template_name = 'quotes/_character_quotes.html'
    context_object_name = 'character'
    slug_url_kwarg = 'character_slug'

    def get_queryset(self):
        return Character.objects.prefetch_related(
            Prefetch(
                'quotes',
                queryset=Quote.objects.filter(
                    visibility=QuoteVisibility.PUBLIC
                ).select_related('author').order_by('-created_at')
            )
        )
```

Si l'auteur consulte ses propres citations, inclure également les citations `PRIVATE`. Les citations `EPHEMERAL` ne sont jamais affichées en liste.

**`htmx_add_quote`** — Endpoint POST pour ajouter une citation (HTMX uniquement).

```python
@login_required
@require_http_methods(["GET", "POST"])
def htmx_add_quote(request, character_slug):
    """
    GET  → retourne le formulaire d'ajout (partial _quote_form.html).
    POST → crée la citation et retourne la carte (_quote_card.html)
            ou le formulaire avec erreurs.
    """
    character = get_object_or_404(Character, slug=character_slug)

    if request.method == 'POST':
        form = QuoteForm(request.POST)
        if form.is_valid():
            quote = form.save(commit=False)
            quote.character = character
            quote.author = request.user
            # report optionnel transmis par paramètre GET
            report_id = request.GET.get('report_id')
            if report_id:
                quote.report = get_object_or_404(Report, id=report_id)
            quote.save()
            return render(request, 'quotes/_quote_card.html', {'quote': quote})
        # Retourner le formulaire avec erreurs
        return render(request, 'quotes/_quote_form.html', {
            'form': form,
            'character': character,
        }, status=422)

    form = QuoteForm()
    return render(request, 'quotes/_quote_form.html', {
        'form': form,
        'character': character,
    })
```

Points clés :
- `GET` sur cet endpoint affiche le formulaire inline (déclenché depuis la fiche personnage ou le compte-rendu via `hx-get`).
- `POST` crée la citation et renvoie directement la carte pour insertion dans la liste (`hx-swap="afterbegin"`).
- Le paramètre `?report_id=` permet de lier optionnellement la citation à un compte-rendu.
- Les citations `EPHEMERAL` ne sont pas fédérées : ne pas déclencher de tâche ActivityPub pour elles.

### 6. Créer apps/quotes/urls.py

```python
"""URL configuration for quotes app."""
from django.urls import path

from . import views

app_name = 'quotes'

urlpatterns = [
    # Liste des citations d'un personnage (partial HTMX ou page complète)
    path(
        'characters/<slug:character_slug>/quotes/',
        views.CharacterQuoteListView.as_view(),
        name='character_quotes'
    ),
    # Formulaire + création (HTMX)
    path(
        'characters/<slug:character_slug>/quotes/add/',
        views.htmx_add_quote,
        name='quote_add'
    ),
]
```

### 7. Créer apps/quotes/forms.py

```python
"""Forms for quotes app."""
from django import forms

from .models import Quote, QuoteVisibility


class QuoteForm(forms.ModelForm):
    """Formulaire d'ajout d'une citation."""

    class Meta:
        model = Quote
        fields = ['content', 'context', 'visibility', 'language']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'La réplique mémorable...',
            }),
            'context': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Situation narrative (optionnel)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Valeur par défaut visible dans le formulaire
        self.fields['visibility'].initial = QuoteVisibility.PUBLIC
        # Le champ language est optionnel — hérité de l'auteur si vide
        self.fields['language'].required = False

    def clean_content(self):
        content = self.cleaned_data['content']
        if len(content.strip()) < 2:
            raise forms.ValidationError(
                "La citation doit contenir au moins 2 caractères."
            )
        return content
```

### 8. Créer apps/quotes/__init__.py

```python
"""Quotes application."""
default_app_config = 'apps.quotes.apps.QuotesConfig'
```

### 9. Enregistrer l'app dans la configuration

Dans `config/settings/base.py`, ajouter `'apps.quotes'` à `INSTALLED_APPS`.

Dans `config/urls.py`, inclure les URLs :

```python
path('', include('apps.quotes.urls', namespace='quotes')),
```

### 10. Créer les templates HTMX

**`templates/quotes/_quote_card.html`** — Partial d'affichage d'une citation :

```html
<div class="quote-card border-l-4 border-gray-300 pl-4 my-3"
     id="quote-{{ quote.id }}">
    <blockquote class="italic text-gray-800">
        "{{ quote.content }}"
    </blockquote>
    {% if quote.context %}
    <p class="text-sm text-gray-500 mt-1">{{ quote.context }}</p>
    {% endif %}
    <p class="text-xs text-gray-400 mt-1">
        — {{ quote.character.name }},
        ajoutée par {{ quote.author.display_name|default:quote.author.username }}
        {% if quote.visibility == 'PRIVATE' %}<span class="ml-1">(privée)</span>{% endif %}
    </p>
</div>
```

**`templates/quotes/_quote_form.html`** — Partial formulaire d'ajout (cible HTMX) :

```html
<form hx-post="{% url 'quotes:quote_add' character.slug %}"
      hx-target="#quote-list-{{ character.id }}"
      hx-swap="afterbegin"
      class="space-y-3 mt-4">
    {% csrf_token %}
    {{ form.content }}
    {{ form.context }}
    <div class="flex gap-4">
        {{ form.visibility }}
        {{ form.language }}
    </div>
    <button type="submit" class="btn btn-primary">Enregistrer la citation</button>
    <button type="button"
            hx-get="{% url 'quotes:character_quotes' character.slug %}"
            hx-target="#quote-form-container-{{ character.id }}"
            hx-swap="innerHTML">
        Annuler
    </button>
</form>
```

**`templates/quotes/_character_quotes.html`** — Partial liste des citations :

```html
<section id="quotes-section-{{ character.id }}">
    <div class="flex justify-between items-center mb-3">
        <h3 class="font-semibold">Citations</h3>
        {% if user.is_authenticated %}
        <button hx-get="{% url 'quotes:quote_add' character.slug %}"
                hx-target="#quote-form-container-{{ character.id }}"
                hx-swap="innerHTML"
                class="btn btn-sm btn-secondary">
            + Ajouter
        </button>
        {% endif %}
    </div>

    <div id="quote-form-container-{{ character.id }}"></div>

    <div id="quote-list-{{ character.id }}">
        {% for quote in character.quotes.all %}
            {% include "quotes/_quote_card.html" %}
        {% empty %}
            <p class="text-gray-500 text-sm">Aucune citation pour l'instant.</p>
        {% endfor %}
    </div>
</section>
```

Ce partial est inclus depuis `templates/characters/detail.html` via :

```html
{% include "quotes/_character_quotes.html" with character=character %}
```

## Validation

- [ ] Modèle Quote importable et migré
- [ ] FK vers Character, User, Report fonctionnelles
- [ ] Admin accessible avec filtres visibility et language
- [ ] Language hérité de l'auteur si non défini
- [ ] Citations EPHEMERAL non listées dans les vues publiques
- [ ] Citations PRIVATE visibles uniquement par leur auteur
- [ ] Formulaire HTMX fonctionnel depuis la fiche personnage
- [ ] Paramètre `?report_id=` lie la citation à un compte-rendu
- [ ] Endpoint POST retourne le partial `_quote_card.html` en cas de succès
- [ ] Endpoint POST retourne 422 + formulaire avec erreurs en cas d'échec

## Notes

- L'app `quotes` dépend de `characters` et `games` — respecter l'ordre des migrations.
- La fédération ActivityPub des citations `PUBLIC` est hors scope de cette tâche (traitée dans la phase 4).
- Les templates supposent que Tailwind CSS est disponible (tâche 06).
- Le champ `language` n'est pas un `choices` field : toute valeur ISO 639-1 libre est acceptée. Une liste de suggestions peut être ajoutée côté template.

## Références

- `docs/models/README.md` — Spécifications Quote et QuoteVisibility
- `docs/memory-bank/user-stories.md` — Domaine 5 : Citations
- `docs/memory-bank/CODEBASE_STRUCTURE.md` — Structure cible `apps/quotes/`
