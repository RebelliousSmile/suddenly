"""Forms for the narrative meta-model (TraitSet / Trait / Action).

Design frontier (issue B / A): the value selector's −5/+5 range is an
UI convenience only. There is deliberately **no** range validation on the
server — ``value`` is a plain nullable IntegerField, so any integer, or none,
is accepted. Do not add Min/MaxValueValidator here or a distribution check:
Suddenly does not know a given system's rules.
"""

from __future__ import annotations

from typing import Any

from django import forms
from django.forms import ModelMultipleChoiceField

from .models import Action, ActionOutcome, Trait, TraitSet


class TraitSetForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = TraitSet
        fields = ["label"]


class TraitForm(forms.ModelForm):  # type: ignore[type-arg]
    # required=False so a valueless tag (Mist) posts an empty value → None.
    # No min_value / max_value: the range lives in the UI, not in validation.
    value = forms.IntegerField(required=False)

    class Meta:
        model = Trait
        fields = ["name", "value", "note"]


class ActionForm(forms.ModelForm):  # type: ignore[type-arg]
    traits: ModelMultipleChoiceField[Trait]

    class Meta:
        model = Action
        fields = ["name", "traits", "condition", "outcome"]

    def __init__(self, *args: Any, trait_set: TraitSet | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        traits_field = self.fields["traits"]
        assert isinstance(traits_field, ModelMultipleChoiceField)
        traits_field.required = False
        # An action only draws on traits from its own set.
        if trait_set is not None:
            traits_field.queryset = trait_set.traits.all()
        else:
            traits_field.queryset = Trait.objects.none()


class ActionOutcomeForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = ActionOutcome
        fields = ["trigger", "text"]
