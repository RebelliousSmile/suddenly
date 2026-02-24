---
name: htmx-component
description: Use when creating HTMX components, partials, interactive elements, or Tailwind-styled templates. Handles hx-* attributes, partial rendering, and infinite scroll.
allowed-tools: Read, Write, Edit, Glob, Grep
---

# HTMX Component Skill

Skill pour créer des composants HTMX + Tailwind selon les conventions Suddenly.

## Architecture Templates

```
templates/
├── base.html                 # Layout principal
├── _navbar.html              # Partials globaux (préfixe _)
├── _messages.html
├── components/               # Composants réutilisables
│   ├── _button.html
│   ├── _card.html
│   ├── _modal.html
│   └── _pagination.html
└── {app}/
    ├── list.html             # Pages complètes
    ├── detail.html
    ├── _card.html            # Partials spécifiques app
    ├── _form.html
    └── _list_item.html
```

## Conventions

### Nommage

| Type | Préfixe | Exemple |
|------|---------|---------|
| Page complète | (aucun) | `list.html`, `detail.html` |
| Partial | `_` | `_card.html`, `_form.html` |
| Composant global | `components/_` | `components/_modal.html` |

### Attributs HTMX

| Attribut | Usage |
|----------|-------|
| `hx-get` | Charger du contenu |
| `hx-post` | Soumettre formulaire |
| `hx-target` | Où injecter la réponse |
| `hx-swap` | Comment injecter (innerHTML, outerHTML, beforeend...) |
| `hx-trigger` | Événement déclencheur |
| `hx-indicator` | Élément loading |
| `hx-push-url` | Mettre à jour l'URL |

## Templates Standards

### Page avec liste HTMX

```html
{# templates/{app}/list.html #}
{% extends "base.html" %}

{% block content %}
<div class="container mx-auto px-4 py-8">
    <div class="flex justify-between items-center mb-6">
        <h1 class="text-2xl font-bold text-gray-900">{{ title }}</h1>
        {% if user.is_authenticated %}
        <a href="{% url '{app}:create' %}" class="btn btn-primary">
            Créer
        </a>
        {% endif %}
    </div>

    {# Liste avec ID pour HTMX #}
    <div id="{app}-list" class="space-y-4">
        {% for item in object_list %}
            {% include "{app}/_card.html" %}
        {% empty %}
            <p class="text-gray-500 text-center py-8">Aucun élément.</p>
        {% endfor %}
    </div>

    {# Infinite scroll #}
    {% if page_obj.has_next %}
    <div hx-get="?page={{ page_obj.next_page_number }}"
         hx-trigger="revealed"
         hx-swap="outerHTML"
         hx-select="#{app}-list > *, [hx-trigger='revealed']"
         class="py-4 text-center">
        <span class="htmx-indicator text-gray-400">Chargement...</span>
    </div>
    {% endif %}
</div>
{% endblock %}
```

### Partial Card

```html
{# templates/{app}/_card.html #}
<article id="{app}-{{ item.id }}"
         class="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow">
    <div class="flex items-start gap-4">
        {% if item.avatar %}
        <img src="{{ item.avatar.url }}"
             alt="{{ item.name }}"
             class="w-12 h-12 rounded-full object-cover">
        {% endif %}

        <div class="flex-1 min-w-0">
            <h3 class="font-semibold text-gray-900 truncate">
                <a href="{{ item.get_absolute_url }}"
                   class="hover:text-blue-600">
                    {{ item.name }}
                </a>
            </h3>
            <p class="text-sm text-gray-500 mt-1 line-clamp-2">
                {{ item.description|truncatewords:30 }}
            </p>
        </div>

        {# Actions HTMX #}
        <div class="flex gap-2">
            {% include "{app}/_actions.html" %}
        </div>
    </div>
</article>
```

### Bouton avec action HTMX

```html
{# templates/{app}/_claim_button.html #}
{% if user.is_authenticated and item.can_be_claimed_by(user) %}
    {% if pending_request %}
        <span class="inline-flex items-center px-3 py-1 rounded-full
                     text-sm bg-yellow-100 text-yellow-800">
            <svg class="animate-spin -ml-1 mr-2 h-4 w-4" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10"
                        stroke="currentColor" stroke-width="4" fill="none"/>
                <path class="opacity-75" fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            En attente...
        </span>
    {% else %}
        <button hx-get="{% url '{app}:claim_modal' item.id %}"
                hx-target="#modal-container"
                hx-swap="innerHTML"
                class="btn btn-primary btn-sm">
            Réclamer
        </button>
    {% endif %}
{% endif %}
```

### Modal HTMX

```html
{# templates/{app}/_modal.html #}
<div id="modal-backdrop"
     class="fixed inset-0 bg-black/50 z-40"
     hx-on:click="htmx.remove('#modal-container > *')">
</div>

<div id="modal-content"
     class="fixed inset-0 z-50 flex items-center justify-center p-4"
     hx-on:click.stop="">
    <div class="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-bold">{{ title }}</h2>
            <button hx-on:click="htmx.remove('#modal-container > *')"
                    class="text-gray-400 hover:text-gray-600">
                <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round"
                          stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
            </button>
        </div>

        <form hx-post="{% url '{app}:claim' item.id %}"
              hx-target="#{app}-{{ item.id }}"
              hx-swap="outerHTML"
              hx-on::after-request="htmx.remove('#modal-container > *')">
            {% csrf_token %}

            <div class="space-y-4">
                {{ form.as_div }}
            </div>

            <div class="flex justify-end gap-3 mt-6">
                <button type="button"
                        hx-on:click="htmx.remove('#modal-container > *')"
                        class="btn btn-secondary">
                    Annuler
                </button>
                <button type="submit" class="btn btn-primary">
                    Confirmer
                </button>
            </div>
        </form>
    </div>
</div>
```

### Formulaire inline

```html
{# templates/{app}/_inline_form.html #}
<form hx-post="{% url '{app}:create' %}"
      hx-target="#{app}-list"
      hx-swap="afterbegin"
      hx-on::after-request="this.reset()"
      class="bg-gray-50 rounded-lg p-4 mb-4">
    {% csrf_token %}

    <div class="flex gap-4">
        <input type="text"
               name="name"
               placeholder="Nom..."
               required
               class="flex-1 rounded border-gray-300 focus:ring-blue-500">

        <button type="submit"
                class="btn btn-primary whitespace-nowrap">
            <span class="htmx-indicator">
                <svg class="animate-spin h-4 w-4" viewBox="0 0 24 24">...</svg>
            </span>
            <span class="htmx-hide-indicator">Ajouter</span>
        </button>
    </div>
</form>
```

## Classes Tailwind Réutilisables

### Boutons (dans base.css ou composant)

```css
/* static/css/components.css */
.btn {
    @apply inline-flex items-center justify-center px-4 py-2
           rounded-lg font-medium transition-colors
           focus:outline-none focus:ring-2 focus:ring-offset-2;
}
.btn-primary {
    @apply bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500;
}
.btn-secondary {
    @apply bg-gray-200 text-gray-700 hover:bg-gray-300 focus:ring-gray-500;
}
.btn-danger {
    @apply bg-red-600 text-white hover:bg-red-700 focus:ring-red-500;
}
.btn-sm {
    @apply px-3 py-1 text-sm;
}
```

## Vue Django pour HTMX

```python
from django.views.decorators.http import require_http_methods
from django.template.response import TemplateResponse

@require_http_methods(["GET"])
def claim_modal(request, pk):
    """Retourne le modal de claim."""
    item = get_object_or_404(Model, pk=pk)
    form = ClaimForm()
    return TemplateResponse(request, '{app}/_modal.html', {
        'item': item,
        'form': form,
        'title': f'Réclamer {item.name}'
    })


@require_http_methods(["POST"])
def claim_action(request, pk):
    """Traite le claim et retourne la card mise à jour."""
    item = get_object_or_404(Model, pk=pk)
    form = ClaimForm(request.POST)

    if form.is_valid():
        # Logique métier
        claim = form.save(commit=False)
        claim.requester = request.user
        claim.target = item
        claim.save()

        # Retourner la card mise à jour
        return TemplateResponse(request, '{app}/_card.html', {
            'item': item,
            'pending_request': claim
        })

    # Erreur : retourner le modal avec erreurs
    return TemplateResponse(request, '{app}/_modal.html', {
        'item': item,
        'form': form,
        'title': f'Réclamer {item.name}'
    }, status=422)
```

## Checklist Composant

- [ ] Partial préfixé avec `_`
- [ ] ID unique pour ciblage HTMX
- [ ] `{% csrf_token %}` dans les forms
- [ ] Indicateur de chargement (`.htmx-indicator`)
- [ ] Gestion des erreurs
- [ ] Accessibilité (aria-*, focus)
- [ ] Responsive (mobile-first)
