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
        }

    def clean_preferred_languages(self) -> list[str]:
        """Convertit la chaîne CSV en liste de codes langue."""
        value = self.cleaned_data.get("preferred_languages")
        if isinstance(value, str):
            return [lang.strip() for lang in value.split(",") if lang.strip()]
        return value or []
