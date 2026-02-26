"""Forms for users app."""

import json

from django import forms

from .models import User


class ProfileForm(forms.ModelForm):
    """Formulaire d'édition du profil utilisateur."""

    class Meta:
        model = User
        fields = [
            "display_name",
            "bio",
            "avatar",
            "content_language",
            "preferred_languages",
            "show_unlabeled_content",
        ]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4}),
            "preferred_languages": forms.TextInput(
                attrs={"placeholder": "fr, en", "class": "form-input"}
            ),
        }

    def clean_preferred_languages(self) -> list[str]:
        """Ensure preferred_languages is a list of language codes.

        Accepts either:
        - Comma-separated values: "fr, en"
        - Valid JSON list: ["fr", "en"]
        """
        value = self.cleaned_data.get("preferred_languages")
        if not value:
            return []

        # Try parsing as JSON first (backward compatibility)
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            # Fall back to comma-separated parsing
            return [
                code.strip()
                for code in value.split(",")
                if code.strip()
            ]
