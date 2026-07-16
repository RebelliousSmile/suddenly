"""URL configuration for the fediverse login flow."""

from django.urls import path

from . import views

app_name = "fediverse_auth"

urlpatterns = [
    path("login/", views.login, name="login"),
    path("callback/", views.callback, name="callback"),
]
