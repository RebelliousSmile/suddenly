"""Views for users app."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import QuerySet
from django.urls import reverse
from django.views.generic import DetailView, UpdateView

from .forms import ProfileForm
from .models import User


class ProfileView(DetailView):
    """Public profile view for a user."""

    model = User
    template_name = "users/profile.html"
    context_object_name = "profile_user"
    slug_field = "username"
    slug_url_kwarg = "username"

    def get_queryset(self) -> QuerySet[User]:
        return User.objects.filter(is_active=True)


class ProfileEditView(LoginRequiredMixin, UpdateView):
    """Edit view for the authenticated user's own profile."""

    model = User
    form_class = ProfileForm
    template_name = "users/profile_edit.html"

    def get_object(self) -> User:
        return self.request.user  # type: ignore[return-value]

    def get_success_url(self) -> str:
        return reverse("users:profile", kwargs={"username": self.request.user.username})
