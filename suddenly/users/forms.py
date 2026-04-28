"""Forms for users app."""

from __future__ import annotations

import json

from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from .models import User


class ProfileForm(forms.ModelForm):  # type: ignore[type-arg]
    """Formulaire d'édition du profil utilisateur."""

    class Meta:
        model = User
        fields = [
            "display_name",
            "bio",
            "avatar",
        ]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4}),
        }


class PreferencesForm(forms.ModelForm):  # type: ignore[type-arg]
    """Formulaire de préférences de langue et d'interface."""

    class Meta:
        model = User
        fields = [
            "content_language",
            "preferred_languages",
            "show_unlabeled_content",
            "interface_language",
        ]
        widgets = {
            "preferred_languages": forms.TextInput(
                attrs={"placeholder": "fr, en", "class": "form-input"}
            ),
            "interface_language": forms.Select(
                choices=[("", _("Use instance default"))] + list(settings.LANGUAGES)
            ),
        }

    def clean_preferred_languages(self) -> list[str]:
        """Ensure preferred_languages is a list of language codes.

        Accepts either:
        - A Python list (from JSONField widget)
        - Comma-separated values: "fr, en"
        - Valid JSON list: '["fr", "en"]'
        """
        value = self.cleaned_data.get("preferred_languages")
        if not value:
            return []

        if isinstance(value, list):
            return [str(code).strip() for code in value if str(code).strip()]

        try:
            result: list[str] = json.loads(value)
            return result
        except (json.JSONDecodeError, TypeError):
            return [code.strip() for code in value.split(",") if code.strip()]
