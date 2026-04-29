"""Forms for RapportMarker entries."""

from __future__ import annotations

from typing import Any

from django import forms
from django.forms import ModelChoiceField

from suddenly.characters.models import Character

from .models import RapportMarker


class RapportMarkerForm(forms.ModelForm):  # type: ignore[type-arg]
    character: ModelChoiceField[Character]

    class Meta:
        model = RapportMarker
        fields = ["kind", "character"]

    def __init__(self, *args: Any, game: Any = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        character_field = self.fields["character"]
        assert isinstance(character_field, ModelChoiceField)
        if game is not None:
            character_field.queryset = Character.objects.filter(origin_game=game).select_related(
                "origin_game"
            )
        else:
            character_field.queryset = Character.objects.none()
