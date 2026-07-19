"""
Core URL patterns.
"""

from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("explorer/", views.explorer, name="explorer"),
    path("populaires/", views.popular_scenes, name="popular_scenes"),
    path("annuaire/", views.directory, name="directory"),
    path("confidentialite/", views.privacy, name="privacy"),
    path("applications/", views.apps, name="apps"),
    path("raccourcis/", views.shortcuts, name="shortcuts"),
    path("signaler/<str:username>/", views.report_user, name="report_user"),
]
