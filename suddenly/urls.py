"""
Suddenly - URL Configuration
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpRequest, JsonResponse
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from suddenly.core import views as core_views


def health_check(request: HttpRequest) -> JsonResponse:
    """Health check endpoint for Docker/load balancers."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    # Health check
    path("health/", health_check, name="health"),
    # Admin
    path("admin/", admin.site.urls),
    # Authentication (django-allauth)
    path("accounts/fediverse/", include("suddenly.fediverse_auth.urls")),
    path("accounts/", include("allauth.urls")),
    # i18n language switcher — wraps Django's set_language so the choice also
    # persists to interface_language for authenticated users.
    path("i18n/setlang/", core_views.switch_language, name="set_language"),
    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="api-docs"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="api-schema"), name="api-redoc"),
    # API
    path("api/", include("suddenly.core.api_urls")),
    # ActivityPub endpoints
    path(".well-known/", include("suddenly.activitypub.wellknown_urls")),
    path("", include("suddenly.activitypub.urls")),  # Inbox endpoints
    # User profiles — @ prefix isolates from all other root patterns
    path("@", include("suddenly.users.urls")),
    # Federation front-end (search, remote profiles)
    path("federation/", include("suddenly.activitypub.federation_urls")),
    # Admin panel (instance admins only — NOT Django admin)
    path("gmh/", include("suddenly.core.admin_urls")),
    path("admin-panel/", RedirectView.as_view(url="/gmh/", permanent=True)),
    # Front-end views (DA-1: HTMX-first)
    path("", include("suddenly.core.front_urls")),
    path("characters/", include("suddenly.characters.front_urls")),
    path("games/", include("suddenly.games.front_urls")),
    path("offers/", include("suddenly.offers.urls")),
    # Docs
    path("docs/", include("suddenly.docs.urls")),
    # Main app
    path("", include("suddenly.core.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
