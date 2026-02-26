"""
Utilitaires communs.
"""
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

    queryset = model_class.objects.all()
    if instance and instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    while queryset.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug
