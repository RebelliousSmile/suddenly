"""Front-end URL patterns for core features (DA-1)."""

from django.urls import path

from . import feed_views, notification_views, onboarding_views

app_name = "feed"

urlpatterns = [
    path("feed/", feed_views.feed_home, name="home"),
    path("feed/instance/", feed_views.feed_instance, name="instance"),
    path("feed/fediverse/", feed_views.feed_fediverse, name="fediverse"),
    path("notifications/", notification_views.notification_list, name="notifications"),
    path(
        "notifications/read-all/",
        notification_views.notification_mark_all_read,
        name="notifications_read_all",
    ),
    path(
        "notifications/badge/",
        notification_views.notification_badge,
        name="notification_badge",
    ),
    path("welcome/", onboarding_views.onboarding_step1, name="onboarding_step1"),
    path("welcome/discover/", onboarding_views.onboarding_step2, name="onboarding_step2"),
    path("welcome/start/", onboarding_views.onboarding_step3, name="onboarding_step3"),
]
