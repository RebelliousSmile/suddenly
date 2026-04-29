"""Forms for Rapport entries."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django import forms
from django.forms import ModelChoiceField

from suddenly.characters.models import Character

from .models import Rapport

if TYPE_CHECKING:
    pass


class RapportForm(forms.ModelForm):  # type: ignore[type-arg]
    actor: ModelChoiceField[Character]

    class Meta:
        model = Rapport
        fields = ["kind", "content", "actor"]

    def __init__(self, *args: Any, game: Any = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        actor_field = self.fields["actor"]
        assert isinstance(actor_field, ModelChoiceField)
        if game is not None:
            actor_field.queryset = Character.objects.filter(origin_game=game).select_related(
                "origin_game"
            )
        else:
            actor_field.queryset = Character.objects.none()
