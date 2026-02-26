"""Forms for users app."""

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
            "preferred_languages": forms.Textarea(attrs={"rows": 2, "class": "form-input"}),
        }

    def clean_preferred_languages(self) -> list[str]:
        """Ensure preferred_languages is a list of language codes."""
        value = self.cleaned_data.get("preferred_languages")
        return value or []
