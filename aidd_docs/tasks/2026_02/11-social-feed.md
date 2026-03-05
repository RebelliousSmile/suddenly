# Tâche 11 : Social Feed — Follow & Fil d'Actualité

**Durée estimée** : 4h
**Phase** : 4 — Fédération & Social
**Statut** : [ ] À faire
**Dépend de** : 04-app-federation, 08-app-characters, 10-app-links

---

## Objectif

Implémenter la logique de suivi (Follow) et le fil d'actualité personnel, en local et cross-instance. Le modèle `Follow` existe déjà (tâche 04) — cette tâche complète la logique manquante : vues de suivi, handlers ActivityPub, et construction du fil.

## Prérequis

- Tâche 04 complétée (`Follow`, `FederatedServer` existent dans `apps/federation/models.py`)
- Tâche 05 complétée (`Game`, `Report` publiables)
- Tâche 08 complétée (`Character` avec `status=NPC` détectable)
- Tâche 10 complétée (`SharedSequence` publiable)

## Fichiers à Créer / Modifier

```
apps/federation/
├── views.py           # Modifier — ajouter htmx_follow, htmx_unfollow
├── services.py        # Créer — FollowService (logique métier)
├── handlers.py        # Modifier — ajouter handle_follow, handle_accept
└── activities.py      # Modifier — ajouter Follow, Accept

apps/users/
└── views.py           # Modifier — FeedView (fil d'actualité)

templates/
├── federation/
│   └── _follow_button.html   # Partial HTMX bouton suivre/ne plus suivre
└── users/
    └── feed.html             # Page fil d'actualité
    └── _feed_item.html       # Partial carte d'élément du fil
    └── _npc_highlight.html   # Partial mise en évidence PNJ disponible
```

---

## Étapes

### 1. Compléter apps/federation/services.py

Créer le service qui centralise la logique de Follow :

```python
"""Service de gestion des abonnements Follow."""
from django.db import transaction
from django.utils import timezone

from apps.federation.models import Follow, FollowStatus, FollowTargetType
from apps.users.models import User


class FollowService:
    """Gère les abonnements entre utilisateurs, personnages et parties."""

    @transaction.atomic
    def follow(
        self,
        follower: User,
        target_type: str,
        target_id,
        target_ap_id: str | None = None,
    ) -> Follow:
        """
        Crée un abonnement.

        - Si la cible est locale : accepté immédiatement (ACCEPTED).
        - Si la cible est distante : en attente (PENDING) jusqu'à réception
          d'une activité Accept dans l'inbox.
        """
        follow, created = Follow.objects.get_or_create(
            follower=follower,
            target_type=target_type,
            target_id=target_id,
            defaults={
                'target_ap_id': target_ap_id,
                'status': (
                    FollowStatus.ACCEPTED
                    if target_ap_id is None
                    else FollowStatus.PENDING
                ),
            },
        )
        return follow

    @transaction.atomic
    def unfollow(self, follower: User, target_type: str, target_id) -> None:
        """Supprime un abonnement existant."""
        Follow.objects.filter(
            follower=follower,
            target_type=target_type,
            target_id=target_id,
        ).delete()

    def is_following(self, follower: User, target_type: str, target_id) -> bool:
        """Vérifie si un abonnement actif existe."""
        return Follow.objects.filter(
            follower=follower,
            target_type=target_type,
            target_id=target_id,
            status=FollowStatus.ACCEPTED,
        ).exists()
```

### 2. Créer les vues HTMX de suivi dans apps/federation/views.py

Les endpoints HTMX retournent uniquement le partial `_follow_button.html` mis à jour.

```python
"""Vues HTMX pour le suivi (Follow/Unfollow)."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.shortcuts import render

from apps.federation.models import FollowTargetType
from apps.federation.services import FollowService
from apps.games.models import Game
from apps.characters.models import Character
from apps.users.models import User


@login_required
@require_http_methods(["POST"])
def htmx_follow_user(request, username):
    """Suivre un joueur (local ou distant)."""
    target = get_object_or_404(User, username=username)
    service = FollowService()
    follow = service.follow(
        follower=request.user,
        target_type=FollowTargetType.USER,
        target_id=target.id,
        target_ap_id=None if target.local else target.ap_id,
    )
    # Si distant : déclencher l'envoi ActivityPub (synchrone ou Celery)
    if not target.local:
        _send_follow_activity(request.user, target)

    return render(request, 'federation/_follow_button.html', {
        'target_type': FollowTargetType.USER,
        'target': target,
        'follow': follow,
        'is_following': True,
    })


@login_required
@require_http_methods(["POST"])
def htmx_unfollow_user(request, username):
    """Ne plus suivre un joueur."""
    target = get_object_or_404(User, username=username)
    service = FollowService()
    service.unfollow(
        follower=request.user,
        target_type=FollowTargetType.USER,
        target_id=target.id,
    )
    return render(request, 'federation/_follow_button.html', {
        'target_type': FollowTargetType.USER,
        'target': target,
        'follow': None,
        'is_following': False,
    })


@login_required
@require_http_methods(["POST"])
def htmx_follow_game(request, game_slug):
    """Suivre une partie."""
    target = get_object_or_404(Game, slug=game_slug, is_public=True)
    service = FollowService()
    follow = service.follow(
        follower=request.user,
        target_type=FollowTargetType.GAME,
        target_id=target.id,
        target_ap_id=None if target.local else target.ap_id,
    )
    return render(request, 'federation/_follow_button.html', {
        'target_type': FollowTargetType.GAME,
        'target': target,
        'follow': follow,
        'is_following': True,
    })


@login_required
@require_http_methods(["POST"])
def htmx_unfollow_game(request, game_slug):
    """Ne plus suivre une partie."""
    target = get_object_or_404(Game, slug=game_slug)
    service = FollowService()
    service.unfollow(
        follower=request.user,
        target_type=FollowTargetType.GAME,
        target_id=target.id,
    )
    return render(request, 'federation/_follow_button.html', {
        'target_type': FollowTargetType.GAME,
        'target': target,
        'follow': None,
        'is_following': False,
    })


@login_required
@require_http_methods(["POST"])
def htmx_follow_character(request, character_slug):
    """Suivre un personnage."""
    target = get_object_or_404(Character, slug=character_slug)
    service = FollowService()
    follow = service.follow(
        follower=request.user,
        target_type=FollowTargetType.CHARACTER,
        target_id=target.id,
        target_ap_id=None if target.local else target.ap_id,
    )
    return render(request, 'federation/_follow_button.html', {
        'target_type': FollowTargetType.CHARACTER,
        'target': target,
        'follow': follow,
        'is_following': True,
    })


@login_required
@require_http_methods(["POST"])
def htmx_unfollow_character(request, character_slug):
    """Ne plus suivre un personnage."""
    target = get_object_or_404(Character, slug=character_slug)
    service = FollowService()
    service.unfollow(
        follower=request.user,
        target_type=FollowTargetType.CHARACTER,
        target_id=target.id,
    )
    return render(request, 'federation/_follow_button.html', {
        'target_type': FollowTargetType.CHARACTER,
        'target': target,
        'follow': None,
        'is_following': False,
    })


def _send_follow_activity(follower: User, target) -> None:
    """Envoie l'activité ActivityPub Follow vers une instance distante."""
    # Déléguer à federation/activities.py
    # Si Celery disponible : tâche async ; sinon : appel synchrone
    from apps.federation.activities import send_follow_activity
    send_follow_activity(follower, target)
```

### 3. Vue Fil d'Actualité dans apps/users/views.py

La vue `FeedView` construit le fil en agrégeant trois types d'éléments, filtrés par les abonnements de l'utilisateur :

- **Reports publiés** des joueurs et parties suivis
- **SharedSequences publiées** impliquant un personnage suivi
- **PNJ disponibles** (status=NPC) apparus récemment dans une partie suivie

```python
"""Vue du fil d'actualité personnel."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.db.models import Q

from apps.federation.models import Follow, FollowStatus, FollowTargetType
from apps.games.models import Report, ReportStatus
from apps.characters.models import Character, CharacterStatus, SharedSequence


class FeedView(LoginRequiredMixin, ListView):
    """
    Fil d'actualité chronologique de l'utilisateur connecté.

    Agrège : comptes-rendus des joueurs/parties suivis,
    Séquences Partagées impliquant des personnages suivis,
    PNJ disponibles mis en évidence.
    """

    template_name = 'users/feed.html'
    context_object_name = 'feed_items'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user

        # Récupérer les IDs suivis acceptés par type
        follows = Follow.objects.filter(
            follower=user,
            status=FollowStatus.ACCEPTED,
        ).values('target_type', 'target_id')

        followed_user_ids = [
            f['target_id'] for f in follows
            if f['target_type'] == FollowTargetType.USER
        ]
        followed_game_ids = [
            f['target_id'] for f in follows
            if f['target_type'] == FollowTargetType.GAME
        ]

        # Comptes-rendus publiés des joueurs et parties suivis
        return (
            Report.objects
            .filter(
                status=ReportStatus.PUBLISHED,
            )
            .filter(
                Q(author_id__in=followed_user_ids) |
                Q(game_id__in=followed_game_ids)
            )
            .select_related('game', 'author')
            .prefetch_related('appearances__character')
            .order_by('-published_at')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # IDs des personnages suivis
        followed_character_ids = list(
            Follow.objects.filter(
                follower=user,
                status=FollowStatus.ACCEPTED,
                target_type=FollowTargetType.CHARACTER,
            ).values_list('target_id', flat=True)
        )

        # IDs des parties suivies
        followed_game_ids = list(
            Follow.objects.filter(
                follower=user,
                status=FollowStatus.ACCEPTED,
                target_type=FollowTargetType.GAME,
            ).values_list('target_id', flat=True)
        )

        # Séquences Partagées récentes impliquant des personnages suivis
        context['shared_sequences'] = (
            SharedSequence.objects
            .filter(
                is_published=True,
            )
            .filter(
                Q(character_link__source_id__in=followed_character_ids) |
                Q(character_link__target_id__in=followed_character_ids)
            )
            .select_related(
                'character_link__source',
                'character_link__target',
                'initiator',
                'acceptor',
            )
            .order_by('-published_at')[:5]
        )

        # PNJ disponibles récents dans les parties suivies
        context['available_npcs'] = (
            Character.objects
            .filter(
                status=CharacterStatus.NPC,
                local=True,
                origin_game_id__in=followed_game_ids,
            )
            .select_related('origin_game', 'creator')
            .order_by('-created_at')[:6]
        )

        return context
```

### 4. Ajouter les URLs

Dans `apps/federation/urls.py` :

```python
"""URL configuration for federation app."""
from django.urls import path
from . import views

app_name = 'federation'

urlpatterns = [
    # Follow / Unfollow — joueurs
    path(
        'follow/user/<str:username>/',
        views.htmx_follow_user,
        name='follow_user',
    ),
    path(
        'unfollow/user/<str:username>/',
        views.htmx_unfollow_user,
        name='unfollow_user',
    ),
    # Follow / Unfollow — parties
    path(
        'follow/game/<slug:game_slug>/',
        views.htmx_follow_game,
        name='follow_game',
    ),
    path(
        'unfollow/game/<slug:game_slug>/',
        views.htmx_unfollow_game,
        name='unfollow_game',
    ),
    # Follow / Unfollow — personnages
    path(
        'follow/character/<slug:character_slug>/',
        views.htmx_follow_character,
        name='follow_character',
    ),
    path(
        'unfollow/character/<slug:character_slug>/',
        views.htmx_unfollow_character,
        name='unfollow_character',
    ),
]
```

Dans `apps/users/urls.py`, ajouter :

```python
path('feed/', views.FeedView.as_view(), name='feed'),
```

### 5. Handler ActivityPub inbox pour Follow/Accept

Dans `apps/federation/handlers.py`, compléter les handlers existants :

```python
"""Handlers pour les activités ActivityPub entrantes."""

def handle_follow(activity: dict, sender_ap_id: str) -> None:
    """
    Traite une activité Follow reçue dans l'inbox.

    Crée un Follow en PENDING, puis envoie automatiquement
    un Accept (les comptes locaux acceptent automatiquement).
    """
    from apps.federation.models import Follow, FollowStatus, FollowTargetType
    from apps.users.models import User

    # Identifier l'objet suivi (User, Game ou Character local)
    object_ap_id = activity.get('object')
    target = _resolve_local_actor(object_ap_id)
    if target is None:
        return  # Cible non trouvée localement

    # Identifier le follower distant
    follower = _get_or_create_remote_user(sender_ap_id)
    if follower is None:
        return

    Follow.objects.update_or_create(
        follower=follower,
        target_type=_get_target_type(target),
        target_id=target.id,
        defaults={
            'target_ap_id': object_ap_id,
            'status': FollowStatus.ACCEPTED,
        },
    )

    # Envoyer Accept en retour
    _send_accept_activity(target, activity, follower)


def handle_accept_follow(activity: dict) -> None:
    """
    Traite une activité Accept en réponse à un Follow envoyé.

    Met à jour le statut du Follow local de PENDING à ACCEPTED.
    """
    from apps.federation.models import Follow, FollowStatus

    original_follow_ap_id = activity.get('object', {}).get('id')
    Follow.objects.filter(
        target_ap_id=activity.get('actor'),
    ).update(status=FollowStatus.ACCEPTED)
```

### 6. Templates HTMX

#### templates/federation/_follow_button.html

```html
{% if user.is_authenticated %}
  {% if is_following %}
    <form hx-post="{% url 'federation:unfollow_'|add:target_type|lower target.slug %}"
          hx-target="this"
          hx-swap="outerHTML">
      {% csrf_token %}
      <button type="submit"
              class="btn btn-secondary text-sm">
        Abonné
      </button>
    </form>
  {% else %}
    <form hx-post="{% url 'federation:follow_'|add:target_type|lower target.slug %}"
          hx-target="this"
          hx-swap="outerHTML">
      {% csrf_token %}
      <button type="submit"
              class="btn btn-primary text-sm">
        Suivre
      </button>
    </form>
  {% endif %}
{% endif %}
```

#### templates/users/feed.html

```html
{% extends "base.html" %}

{% block content %}
<div class="container mx-auto px-4 py-6">
  <h1 class="text-2xl font-bold mb-6">Mon fil d'actualité</h1>

  {# PNJ disponibles mis en évidence #}
  {% if available_npcs %}
    <section class="mb-8">
      <h2 class="text-lg font-semibold mb-3 text-amber-700">
        PNJ disponibles dans vos parties suivies
      </h2>
      <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
        {% for npc in available_npcs %}
          {% include "users/_npc_highlight.html" %}
        {% endfor %}
      </div>
    </section>
  {% endif %}

  {# Séquences Partagées récentes #}
  {% if shared_sequences %}
    <section class="mb-8">
      <h2 class="text-lg font-semibold mb-3 text-purple-700">
        Séquences Partagées récentes
      </h2>
      {% for seq in shared_sequences %}
        <div class="border rounded p-4 mb-3 bg-purple-50">
          <p class="font-medium">{{ seq.title }}</p>
          <p class="text-sm text-gray-600">
            Entre {{ seq.initiator.display_name }} et {{ seq.acceptor.display_name }}
          </p>
          <p class="text-sm">
            {{ seq.character_link.source.name }} ↔ {{ seq.character_link.target.name }}
          </p>
        </div>
      {% endfor %}
    </section>
  {% endif %}

  {# Comptes-rendus chronologiques #}
  <section>
    <h2 class="text-lg font-semibold mb-3">Comptes-rendus récents</h2>
    <div id="feed-list" class="space-y-4">
      {% for report in feed_items %}
        {% include "users/_feed_item.html" %}
      {% endfor %}
    </div>

    {% if page_obj.has_next %}
      <div hx-get="?page={{ page_obj.next_page_number }}"
           hx-trigger="revealed"
           hx-swap="afterend"
           hx-select="#feed-list > *"
           class="text-center py-4 text-gray-400">
        Chargement...
      </div>
    {% endif %}

    {% if not feed_items %}
      <p class="text-gray-500 text-center py-12">
        Votre fil est vide. Suivez des joueurs ou des parties pour voir leurs publications ici.
      </p>
    {% endif %}
  </section>
</div>
{% endblock %}
```

#### templates/users/_feed_item.html

```html
<article class="border rounded-lg p-4 bg-white shadow-sm">
  <div class="flex items-center gap-3 mb-2">
    {% if report.author.avatar %}
      <img src="{{ report.author.avatar.url }}"
           alt="{{ report.author.display_name }}"
           class="w-8 h-8 rounded-full">
    {% endif %}
    <div>
      <a href="{% url 'users:profile' report.author.username %}"
         class="font-medium hover:underline">
        {{ report.author.display_name|default:report.author.username }}
      </a>
      <span class="text-gray-400 text-sm mx-1">dans</span>
      <a href="{% url 'games:game_detail' report.game.slug %}"
         class="text-gray-600 hover:underline text-sm">
        {{ report.game.title }}
      </a>
    </div>
    <time class="ml-auto text-gray-400 text-xs"
          datetime="{{ report.published_at|date:'c' }}">
      {{ report.published_at|timesince }}
    </time>
  </div>

  <h3 class="font-semibold text-lg mb-1">
    <a href="{{ report.get_absolute_url }}" class="hover:underline">
      {{ report.title }}
    </a>
  </h3>

  {% if report.appearances.all %}
    <div class="flex flex-wrap gap-1 mt-2">
      {% for appearance in report.appearances.all|slice:":5" %}
        <span class="text-xs px-2 py-0.5 rounded-full
          {% if appearance.character.status == 'NPC' %}
            bg-amber-100 text-amber-800
          {% else %}
            bg-blue-100 text-blue-800
          {% endif %}">
          {{ appearance.character.name }}
          {% if appearance.character.status == 'NPC' %}
            <span title="PNJ disponible">★</span>
          {% endif %}
        </span>
      {% endfor %}
    </div>
  {% endif %}
</article>
```

#### templates/users/_npc_highlight.html

```html
<div class="border border-amber-300 rounded-lg p-3 bg-amber-50">
  <p class="font-medium text-sm">{{ npc.name }}</p>
  <p class="text-xs text-gray-500 mb-2">{{ npc.origin_game.title }}</p>
  <a href="{% url 'characters:character_detail' npc.slug %}"
     class="text-xs text-amber-700 hover:underline font-medium">
    Voir la fiche →
  </a>
</div>
```

---

## Intégration du bouton "Suivre" sur les pages existantes

Le partial `_follow_button.html` doit être inclus dans trois emplacements :

**Profil joueur** (`templates/users/profile.html`) :
```html
{% include "federation/_follow_button.html" with target=profile_user target_type="USER" is_following=is_following %}
```

**Page de partie** (`templates/games/game_detail.html`) :
```html
{% include "federation/_follow_button.html" with target=game target_type="GAME" is_following=is_following %}
```

**Fiche personnage** (`templates/characters/character_detail.html`) :
```html
{% include "federation/_follow_button.html" with target=character target_type="CHARACTER" is_following=is_following %}
```

Chaque vue associée doit passer `is_following` dans son contexte :

```python
context['is_following'] = FollowService().is_following(
    follower=request.user,
    target_type=FollowTargetType.USER,  # adapter selon la page
    target_id=target.id,
)
```

---

## Follow Cross-Instance (ActivityPub)

### Flux Outgoing (utilisateur local suit une cible distante)

```
1. Utilisateur clique "Suivre" sur un profil distant
2. htmx_follow_user() → FollowService.follow() → Follow(status=PENDING)
3. _send_follow_activity() → POST vers inbox de la cible
4. Instance distante envoie Accept → handle_accept_follow()
5. Follow.status → ACCEPTED
6. Les publications de la cible apparaissent dans le feed local via Announce
```

### Flux Incoming (utilisateur distant suit une cible locale)

```
1. Instance distante POST /inbox avec activité Follow
2. InboxView → verify_signature() → handle_follow()
3. Follow(status=ACCEPTED) créé côté local
4. Accept envoyé automatiquement en retour
5. Les activités locales sont désormais livrées à l'instance distante
```

### Points clés

- Les comptes locaux **acceptent automatiquement** tous les follows (pas de validation manuelle).
- Les follows distants sont créés en `PENDING` jusqu'à réception du `Accept`.
- Le champ `target_ap_id` stocke l'URL AP de la cible pour les suivis cross-instance.
- Le modèle `Follow` est **polymorphique** : `target_type` + `target_id` → User, Game ou Character.

---

## Validation

- [ ] Le bouton "Suivre" apparaît sur les profils joueurs, pages de parties et fiches personnages
- [ ] Cliquer "Suivre" crée un `Follow(status=ACCEPTED)` pour une cible locale
- [ ] Cliquer "Ne plus suivre" supprime le `Follow`
- [ ] Le fil d'actualité liste les comptes-rendus des joueurs et parties suivis
- [ ] Les PNJ disponibles dans les parties suivies sont mis en évidence
- [ ] Les Séquences Partagées impliquant des personnages suivis apparaissent
- [ ] Le fil est paginé (20 éléments par page, pagination infinie HTMX)
- [ ] Un Follow cross-instance crée un `Follow(status=PENDING)` jusqu'au Accept
- [ ] L'inbox handler `handle_follow` accepte et répond automatiquement

## Notes

- La livraison des activités AP vers les instances distantes doit être async si Celery est disponible, synchrone sinon (voir pattern établi en tâche 04).
- `SharedSequence` est référencé ici depuis `apps.characters.models` — vérifier que l'import est correct selon l'état de la tâche 10.
- Le fil ne filtre pas encore par langue (voir préférences `User.preferred_languages`) — à ajouter dans une itération future.
- Les templates sont minimalistes — le style Tailwind sera affiné lors de la tâche 06 (templates de base).

## Références

- `docs/models/README.md` — Follow, FederatedServer (modèles détaillés)
- `docs/memory-bank/ARCHITECTURE.md` — flux ActivityPub Inbox/Outbox
- `docs/memory-bank/user-stories.md` — Domaine 7 (Suivre une partie, Voir mon fil)
