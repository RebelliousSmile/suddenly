# Explorer — Navigation refactor + page de découverte fusionnée

## Feature

- **Summary**: Refactor nav (suppression Mes parties/Mes personnages, ajout Jouer → /feed/, Explorer → /explorer/), extraction des queryset builders vers services, création page Explorer unifiée avec hero, tabs Personnages/Parties, tagline et loupe
- **Stack**: `Django 5.0`, `HTMX`, `Alpine.js`, `UnoCSS`
- **Branch name**: `feat/explorer-nav-refactor`
- **Parent Plan**: none
- **Sequence**: standalone
- Confidence: 9/10
- Time to implement: 3h

## Existing files

- @templates/base.html
- @suddenly/core/views.py
- @suddenly/core/urls.py
- @suddenly/characters/services.py
- @suddenly/characters/front_views.py
- @suddenly/games/front_views.py
- @templates/characters/_list_results.html
- @templates/games/_list_results.html
- @templates/components/tag_filter.html
- @templates/feed/home.html
- @locale/fr/LC_MESSAGES/django.po

### New files to create

- `templates/core/explorer.html`
- `suddenly/games/services.py`

## User Journey

```mermaid
flowchart TD
  A[Utilisateur] --> B{Nav}
  B -->|Explorer| C[/explorer/ — page fusionnée]
  B -->|Jouer| D[/feed/ — fil fédéré existant]
  B -->|Accueil| E[/ — home inchangé]

  C --> F{Tab actif}
  F -->|Personnages défaut| G[Hero + search + filtres status/system/tags]
  F -->|Parties| H[Hero + search + filtres system/tags]

  G -->|recherche HTMX| I[characters/_list_results.html]
  H -->|recherche HTMX| J[games/_list_results.html]
```

## Implementation phases

### Phase 1 — Navigation

> Supprimer Mes parties / Mes personnages du nav, câbler Explorer et Jouer

1. Dans `base.html` nav desktop : supprimer le bloc "My games" (`games:list`, icône `i-lucide-book-open`) et "My characters" (`characters:list`, icône `i-lucide-users`) — ces deux liens sont **dans** le bloc `{% if user.is_authenticated %}`
2. Changer `href="#"` de "Explore" → `{% url 'core:explorer' %}` — ce lien est hors du bloc auth, le garder hors du bloc
3. Ajouter "Jouer" → `{% url 'feed:home' %}` **hors** du bloc `{% if user.is_authenticated %}`, juste après "Explorer", sans icône
4. Appliquer les mêmes changements au nav mobile

### Phase 2 — Extraction des queryset builders vers services

> Rendre les queryset builders accessibles publiquement pour éviter la duplication (règle DRY : 2 appelants)

1. Dans `suddenly/characters/services.py` : extraire `_build_character_queryset` depuis `front_views.py` → nouvelle fonction publique `build_character_queryset(request: HttpRequest) -> QuerySet[Character]` — logique identique, inclut FTS (`SearchQuery`, `SearchVector`, `SearchRank`, config `french`)
2. Créer `suddenly/games/services.py` : y déplacer `_build_game_queryset` depuis `front_views.py` → `build_game_queryset(request: HttpRequest) -> QuerySet[Game]`
3. Dans `characters/front_views.py` : remplacer l'appel à `_build_character_queryset` par `build_character_queryset` importé depuis `services`
4. Dans `games/front_views.py` : remplacer l'appel à `_build_game_queryset` par `build_game_queryset` importé depuis `services`
5. Supprimer les anciennes fonctions `_build_*` dans les front_views (elles sont maintenant dans services)

### Phase 3 — Page Explorer

> Nouvelle vue + URL + template : hero, tabs Personnages/Parties, search avec loupe, résultats pré-rendus, contexte Alpine sur le container

**Vue** `suddenly/core/views.py` — ajouter `explorer()` :
- Accepte `?tab=characters` (défaut) ou `?tab=games`
- Appelle `build_character_queryset(request)` ou `build_game_queryset(request)` selon le tab (importés depuis leurs `services.py` respectifs)
- Collecte `all_tags` du modèle actif (Character ou Game, `remote=False, tags__isnull=False`)
- Passe `statuses=CharacterStatus.choices` uniquement pour le tab `characters`
- Note : Character n'a pas de champ `is_public` — tous les personnages locaux (`remote=False`) sont publics par design actuel
- Contexte : `active_tab`, `characters`/`games` (résultats pré-rendus `[:24]`), `query`, `status_filter`, `system_filter`, `active_tag`, `all_tags`, `statuses`
- `return render(request, "core/explorer.html", context)` — pas de `htmx_render`, Explorer est une page complète

**URL** `suddenly/core/urls.py` : ajouter `path("explorer/", views.explorer, name="explorer")`

**Template** `templates/core/explorer.html` :
- Outer container : `<div class="container-app" x-data="{ selectMode: false }">` — le `x-data` est sur le container, **pas** sur `div#explorer-results` (miroir du pattern `characters/list.html` et `games/list.html`)
- Hero : `<section class="bg-gradient-to-br from-surface to-background py-12">`, `<h1>` headline, `<p>` tagline i18n
- Tagline : `{% trans "avec quel personnage vous voulez jouer aujourd'hui ?" %}`
- Tab nav (pattern `link_requests.html`) : `?tab=characters` / `?tab=games`, `border-crimson text-crimson` actif
- Search input dans un `<div class="relative">` : `<input hx-get hx-trigger="keyup changed delay:300ms" hx-target="#explorer-results" ...>` + `<span class="i-lucide-search absolute right-3 top-1/2 -translate-y-1/2 text-muted pointer-events-none">`
  - `hx-get` = `{% url 'characters:search' %}` ou `{% url 'games:search' %}` selon `active_tab`
  - `hx-include` = `[name='status'],[name='system'],[name='tag']` (characters) ou `[name='system'],[name='tag']` (games)
- Filtres : status select (tab characters uniquement) + system input + `{% include "components/tag_filter.html" ... %}`
- `<div id="explorer-results">{% include "characters/_list_results.html" %}` (ou games) — résultats pré-rendus, pas de `hx-trigger="load"`

### Phase 4 — i18n

> Nouvelles chaînes traduites, .po recompilé

1. Lancer `python manage.py makemessages -l fr -l en --no-wrap --ignore=venv --ignore=node_modules`
2. Traduire dans `locale/fr/LC_MESSAGES/django.po` :
   - `"Play"` → `"Jouer"` (nouvelle chaîne nav)
   - Tagline (nouvelle chaîne)
   - Vérifier que `"Explore"` → `"Explorer"` est déjà présent
3. Lancer `python manage.py compilemessages -l fr -l en`

## Validation flow

1. Nav affiche : Accueil / Explorer / Jouer / [dropdown user si connecté] — sans icônes sur Explorer et Jouer
2. Explorer et Jouer visibles pour utilisateurs anonymes ET authentifiés
3. "Mes parties" et "Mes personnages" ont disparu du nav (desktop + mobile)
4. `/explorer/` affiche hero avec headline + tagline + icône loupe dans le champ
5. Tab "Personnages" actif par défaut : liste pré-rendue, recherche HTMX fonctionne (FTS inclus), filtres status/system/tags fonctionnent
6. Tab "Parties" : liste pré-rendue, recherche HTMX fonctionne, filtres system/tags fonctionnent
7. Pas d'erreur Alpine.js console (`selectMode` bien défini sur le container outer)
8. `/feed/` (Jouer) s'affiche correctement
9. `make check` passe (lint + typecheck + i18n + tests)
