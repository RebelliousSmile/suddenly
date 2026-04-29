"""Admin panel URL patterns (separate from Django admin)."""

from django.urls import path

from . import admin_views

app_name = "gmh"

urlpatterns = [
    path("", admin_views.admin_dashboard, name="dashboard"),
    path("instances/", admin_views.admin_instances, name="instances"),
    path(
        "instances/<uuid:pk>/block/",
        admin_views.admin_instance_block,
        name="instance_block",
    ),
    path(
        "instances/<uuid:pk>/unblock/",
        admin_views.admin_instance_unblock,
        name="instance_unblock",
    ),
    path("settings/", admin_views.instance_settings, name="instance_settings"),
    path("users/", admin_views.admin_users, name="users"),
    path(
        "users/<uuid:pk>/suspend/",
        admin_views.admin_user_suspend,
        name="user_suspend",
    ),
]
