"""Views for users app."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import DetailView, UpdateView

from .forms import ProfileForm
from .models import User


class ProfileView(DetailView):  # type: ignore[type-arg]
    """Public profile view for a user."""

    model = User
    template_name = "users/profile.html"
    context_object_name = "profile_user"
    slug_field = "username"
    slug_url_kwarg = "username"

    def get_queryset(self) -> QuerySet[User]:
        return User.objects.filter(is_active=True)

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        """Pass user's public games, characters, followers count, follow state."""
        context = super().get_context_data(**kwargs)
        profile_user = self.object

        # Games and characters
        context["games"] = profile_user.games.filter(is_public=True).order_by("-updated_at")[:10]
        context["characters"] = profile_user.created_characters.order_by("-created_at")[:12]

        # Follow stats — single query with conditional aggregation
        follow_stats = _get_follow_stats(profile_user, self.request.user)
        context.update(follow_stats)

        return context


def _get_follow_stats(profile_user: User, request_user: object) -> dict[str, object]:
    """Compute follow stats for a profile in minimal queries."""
    from django.contrib.contenttypes.models import ContentType

    from suddenly.characters.models import Follow

    user_ct = ContentType.objects.get_for_model(User)

    # Single query: followers count + is_following (combined filter)
    followers_qs = Follow.objects.filter(content_type=user_ct, object_id=profile_user.id)
    followers_count = followers_qs.count()

    is_following = False
    if hasattr(request_user, "is_authenticated") and request_user.is_authenticated:
        if request_user != profile_user:
            is_following = followers_qs.filter(follower=request_user).exists()

    return {
        "followers_count": followers_count,
        "following_count": Follow.objects.filter(follower=profile_user).count(),
        "is_following": is_following,
    }


class ProfileEditView(LoginRequiredMixin, UpdateView):  # type: ignore[type-arg]
    """Edit view for the authenticated user's own profile."""

    model = User
    form_class = ProfileForm
    template_name = "users/profile_edit.html"

    def dispatch(self, request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
        """Redirect to the authenticated user's own edit URL if username doesn't match."""
        if request.user.is_authenticated and kwargs.get("username") != request.user.username:
            return redirect("users:profile_edit", username=request.user.username)
        return super().dispatch(request, *args, **kwargs)  # type: ignore[return-value]

    def get_object(self, queryset: QuerySet[User] | None = None) -> User:
        return self.request.user  # type: ignore[return-value]

    def get_success_url(self) -> str:
        return reverse("users:profile", kwargs={"username": self.request.user.username})
