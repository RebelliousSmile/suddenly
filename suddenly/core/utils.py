"""
Utilitaires communs.
"""

from typing import Any

from django.db import models
from django.utils.text import slugify as django_slugify


def generate_unique_slug(
    model_class: type[models.Model],
    value: str,
    instance: models.Model | None = None,
) -> str:
    """
    Génère un slug unique pour un modèle donné.

    Args:
        model_class: La classe du modèle cible
        value: La valeur à slugifier
        instance: Instance existante à exclure (pour les updates)

    Returns:
        Slug unique garanti pour ce modèle

    Note:
        Le modèle doit posséder un champ `slug`.
    """
    base_slug = django_slugify(value)
    slug = base_slug
    counter = 1

    queryset = model_class._default_manager.all()
    if instance and instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    while queryset.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug


# =================================================================
# Actor type resolution (audit rows 1, 26)
# =================================================================
#
# Single source for the "user"/"game"/"character" actor-kind -> Model
# mapping, previously hand-rolled at 9 sites (inbox dispatch, outbound
# delivery task routing, Follow target resolution). Casing-normalized:
# tasks.py historically used PascalCase keys ("User"/"Game"/"Character",
# mirroring the AP `type` field) while inbox.py/views used lowercase
# ("user"/"game"/"character", URL path segments) — both resolve here.


def actor_model_for(type_key: str) -> type[models.Model]:
    """Resolve an actor type key (any casing) to its Django model.

    Args:
        type_key: One of "user"/"game"/"character", any casing.

    Returns:
        The corresponding model class.

    Raises:
        ValueError: `type_key` is not a recognized actor type.
    """
    from suddenly.characters.models import Character
    from suddenly.games.models import Game
    from suddenly.users.models import User

    models_by_key: dict[str, type[models.Model]] = {
        "user": User,
        "game": Game,
        "character": Character,
    }
    model = models_by_key.get(type_key.lower())
    if model is None:
        raise ValueError(f"Unknown actor type: {type_key!r}")
    return model


def content_type_for_actor(type_key: str) -> Any:
    """Return the `ContentType` for an actor type key. See `actor_model_for`.

    Raises:
        ValueError: `type_key` is not a recognized actor type.
    """
    from django.contrib.contenttypes.models import ContentType

    return ContentType.objects.get_for_model(actor_model_for(type_key))


def get_local_actor(actor_type: str, identifier: str) -> Any:
    """Look up a local (non-remote) actor by type + identifier.

    `user` is keyed by `username`; `game`/`character` are keyed by `id`
    (UUID pk). Returns `None` for an unknown type or a missing row —
    never raises, unlike `actor_model_for`.
    """
    try:
        model = actor_model_for(actor_type)
    except ValueError:
        return None

    lookup_field = "username" if actor_type.lower() == "user" else "id"
    return model._default_manager.filter(**{lookup_field: identifier}, remote=False).first()
