# Tâche 06 : Templates de Base

**Durée estimée** : 1h
**Phase** : 1 - Fondations
**Statut** : [ ] À faire
**Dépend de** : 05-app-games

---

## Objectif

Créer les templates de base avec HTMX et Tailwind CSS : layout principal, navbar, et templates pour les apps users et games.

## Prérequis

- Tâches 01-05 complétées
- Apps users et games fonctionnelles

## Fichiers à Créer

```
templates/
├── base.html                    # Layout principal
├── components/
│   ├── _navbar.html             # Navigation
│   ├── _messages.html           # Flash messages
│   └── _pagination.html         # Pagination HTMX
├── users/
│   ├── profile.html             # Profil utilisateur
│   └── profile_edit.html        # Édition profil
└── games/
    ├── home.html                # Page d'accueil
    ├── game_detail.html         # Détail partie
    ├── game_form.html           # Création/édition partie
    ├── report_detail.html       # Détail compte-rendu
    ├── report_form.html         # Création/édition report
    ├── _game_card.html          # Carte partie (partial)
    └── _report_card.html        # Carte report (partial)
```

## Étapes

### 1. Créer templates/base.html

```html
<!DOCTYPE html>
<html lang="fr" class="h-full">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Suddenly{% endblock %}</title>

    <!-- Tailwind CSS (CDN pour dev) -->
    <script src="https://cdn.tailwindcss.com"></script>

    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>

    {% block extra_head %}{% endblock %}
</head>
<body class="h-full bg-gray-50" hx-boost="true">
    {% include "components/_navbar.html" %}

    <!-- Messages flash -->
    {% include "components/_messages.html" %}

    <!-- Contenu principal -->
    <main class="container mx-auto px-4 py-8">
        {% block content %}{% endblock %}
    </main>

    <!-- Footer -->
    <footer class="bg-gray-800 text-gray-300 mt-auto">
        <div class="container mx-auto px-4 py-6 text-center text-sm">
            <p>Suddenly — Réseau fédéré de fiction partagée</p>
            <p class="mt-1 text-gray-500">
                <a href="https://github.com/votre-compte/suddenly" class="hover:text-white">GitHub</a>
            </p>
        </div>
    </footer>

    <!-- Modal container pour HTMX -->
    <div id="modal-container"></div>

    {% block extra_js %}{% endblock %}
</body>
</html>
```

### 2. Créer templates/components/_navbar.html

```html
<nav class="bg-white shadow">
    <div class="container mx-auto px-4">
        <div class="flex justify-between items-center h-16">
            <!-- Logo -->
            <a href="{% url 'games:home' %}" class="text-xl font-bold text-gray-900">
                Suddenly
            </a>

            <!-- Navigation -->
            <div class="flex items-center gap-4">
                <a href="{% url 'games:game_list' %}"
                   class="text-gray-600 hover:text-gray-900">
                    Parties
                </a>

                {% if user.is_authenticated %}
                    <a href="{% url 'games:game_create' %}"
                       class="text-gray-600 hover:text-gray-900">
                        Nouvelle partie
                    </a>
                    <div class="relative" x-data="{ open: false }">
                        <button @click="open = !open"
                                class="flex items-center gap-2 text-gray-600 hover:text-gray-900">
                            {% if user.avatar %}
                                <img src="{{ user.avatar.url }}"
                                     alt="{{ user.username }}"
                                     class="w-8 h-8 rounded-full">
                            {% else %}
                                <span class="w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center">
                                    {{ user.username|slice:":1"|upper }}
                                </span>
                            {% endif %}
                            {{ user.get_display_name }}
                        </button>
                        <!-- Dropdown menu -->
                        <div x-show="open" @click.away="open = false"
                             class="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg py-1 z-50">
                            <a href="{% url 'users:profile' user.username %}"
                               class="block px-4 py-2 text-gray-700 hover:bg-gray-100">
                                Mon profil
                            </a>
                            <a href="{% url 'account_logout' %}"
                               class="block px-4 py-2 text-gray-700 hover:bg-gray-100">
                                Déconnexion
                            </a>
                        </div>
                    </div>
                {% else %}
                    <a href="{% url 'account_login' %}"
                       class="text-gray-600 hover:text-gray-900">
                        Connexion
                    </a>
                    <a href="{% url 'account_signup' %}"
                       class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
                        Inscription
                    </a>
                {% endif %}
            </div>
        </div>
    </div>
</nav>

<!-- Alpine.js pour le dropdown (optionnel, peut utiliser HTMX) -->
<script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
```

### 3. Créer templates/components/_messages.html

```html
{% if messages %}
<div class="container mx-auto px-4 mt-4">
    {% for message in messages %}
    <div class="p-4 rounded-lg mb-2 {% if message.tags == 'error' %}bg-red-100 text-red-800{% elif message.tags == 'success' %}bg-green-100 text-green-800{% else %}bg-blue-100 text-blue-800{% endif %}"
         role="alert">
        {{ message }}
    </div>
    {% endfor %}
</div>
{% endif %}
```

### 4. Créer templates/components/_pagination.html

```html
{% if page_obj.has_other_pages %}
<nav class="flex justify-center mt-8" aria-label="Pagination">
    <ul class="flex gap-2">
        {% if page_obj.has_previous %}
        <li>
            <a href="?page={{ page_obj.previous_page_number }}"
               class="px-4 py-2 rounded-lg bg-white shadow hover:bg-gray-50">
                Précédent
            </a>
        </li>
        {% endif %}

        <li class="px-4 py-2 text-gray-600">
            Page {{ page_obj.number }} / {{ page_obj.paginator.num_pages }}
        </li>

        {% if page_obj.has_next %}
        <li>
            <a href="?page={{ page_obj.next_page_number }}"
               hx-get="?page={{ page_obj.next_page_number }}"
               hx-target="#game-list"
               hx-swap="beforeend"
               hx-select="#game-list > *"
               class="px-4 py-2 rounded-lg bg-white shadow hover:bg-gray-50">
                Suivant
            </a>
        </li>
        {% endif %}
    </ul>
</nav>
{% endif %}
```

### 5. Créer templates/games/home.html

```html
{% extends "base.html" %}

{% block title %}Parties — Suddenly{% endblock %}

{% block content %}
<div class="mb-8">
    <h1 class="text-3xl font-bold text-gray-900">Parties récentes</h1>
    <p class="mt-2 text-gray-600">Découvrez les dernières histoires partagées</p>
</div>

<div id="game-list" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
    {% for game in games %}
        {% include "games/_game_card.html" %}
    {% empty %}
        <p class="col-span-full text-center text-gray-500 py-12">
            Aucune partie pour le moment.
            {% if user.is_authenticated %}
            <a href="{% url 'games:game_create' %}" class="text-blue-600 hover:underline">
                Créez la première !
            </a>
            {% endif %}
        </p>
    {% endfor %}
</div>

{% include "components/_pagination.html" %}
{% endblock %}
```

### 6. Créer templates/games/_game_card.html

```html
<article class="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow">
    <div class="p-6">
        <div class="flex items-start justify-between">
            <div>
                <h2 class="text-xl font-semibold text-gray-900">
                    <a href="{{ game.get_absolute_url }}" class="hover:text-blue-600">
                        {{ game.title }}
                    </a>
                </h2>
                {% if game.game_system %}
                <span class="inline-block mt-1 px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-600">
                    {{ game.game_system }}
                </span>
                {% endif %}
            </div>
        </div>

        {% if game.description %}
        <p class="mt-3 text-gray-600 line-clamp-2">
            {{ game.description|truncatewords:30 }}
        </p>
        {% endif %}

        <div class="mt-4 flex items-center text-sm text-gray-500">
            <a href="{% url 'users:profile' game.owner.username %}"
               class="hover:text-blue-600">
                {{ game.owner.get_display_name }}
            </a>
            <span class="mx-2">•</span>
            <span>{{ game.created_at|date:"d M Y" }}</span>
        </div>
    </div>
</article>
```

### 7. Créer templates/games/game_detail.html

```html
{% extends "base.html" %}

{% block title %}{{ game.title }} — Suddenly{% endblock %}

{% block content %}
<div class="max-w-4xl mx-auto">
    <!-- Header -->
    <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-900">{{ game.title }}</h1>
        {% if game.game_system %}
        <span class="inline-block mt-2 px-3 py-1 text-sm rounded-full bg-blue-100 text-blue-800">
            {{ game.game_system }}
        </span>
        {% endif %}

        <div class="mt-4 flex items-center text-gray-600">
            <span>Par</span>
            <a href="{% url 'users:profile' game.owner.username %}"
               class="ml-1 text-blue-600 hover:underline">
                {{ game.owner.get_display_name }}
            </a>
        </div>

        {% if game.description %}
        <div class="mt-4 text-gray-700">
            {{ game.description|linebreaks }}
        </div>
        {% endif %}
    </div>

    <!-- Actions -->
    {% if user == game.owner %}
    <div class="mb-6 flex gap-4">
        <a href="{% url 'games:game_update' game.slug %}"
           class="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300">
            Modifier
        </a>
        <a href="{% url 'games:report_create' game.slug %}"
           class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            Nouveau compte-rendu
        </a>
    </div>
    {% endif %}

    <!-- Reports -->
    <section>
        <h2 class="text-2xl font-bold text-gray-900 mb-4">Comptes-rendus</h2>

        <div class="space-y-4">
            {% for report in reports %}
                {% include "games/_report_card.html" %}
            {% empty %}
                <p class="text-gray-500 py-8 text-center">
                    Aucun compte-rendu publié.
                </p>
            {% endfor %}
        </div>
    </section>
</div>
{% endblock %}
```

### 8. Créer les templates restants

Créer également :
- `templates/games/_report_card.html`
- `templates/games/game_form.html`
- `templates/games/report_detail.html`
- `templates/games/report_form.html`
- `templates/users/profile.html`
- `templates/users/profile_edit.html`

(Suivre le même pattern que les exemples ci-dessus)

## Validation

- [ ] Page d'accueil affiche les parties
- [ ] Navigation fonctionne
- [ ] Styles Tailwind appliqués
- [ ] HTMX chargé (vérifier console)
- [ ] Responsive (mobile/desktop)

## Notes

- Tailwind via CDN pour le dev — en production, build local
- Alpine.js optionnel pour le dropdown (peut être remplacé par HTMX)
- Les partials commencent par `_` (convention)

## Références

- `documentation/memory-bank/02-development-standards.md` — Conventions templates
- `.claude/skills/htmx-component/SKILL.md` — Patterns HTMX
