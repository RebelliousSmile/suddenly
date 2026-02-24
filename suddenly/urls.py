"""
Suddenly - URL Configuration
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)


def health_check(request):
    """Health check endpoint for Docker/load balancers."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    # Health check
    path("health/", health_check, name="health"),
    
    # Admin
    path("admin/", admin.site.urls),
    
    # Authentication (django-allauth)
    path("accounts/", include("allauth.urls")),
    
    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="api-docs"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="api-schema"), name="api-redoc"),
    
    # API
    path("api/", include("suddenly.core.api_urls")),
    
    # ActivityPub endpoints
    path(".well-known/", include("suddenly.activitypub.wellknown_urls")),
    path("", include("suddenly.activitypub.urls")),  # Inbox endpoints
    
    # Main app
    path("", include("suddenly.core.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
