"""Front-end URL patterns for core features (DA-1)."""

from django.urls import path

from . import feed_views

app_name = "feed"

urlpatterns = [
    path("feed/", feed_views.feed_home, name="home"),
    path("feed/instance/", feed_views.feed_instance, name="instance"),
    path("feed/fediverse/", feed_views.feed_fediverse, name="fediverse"),
]
