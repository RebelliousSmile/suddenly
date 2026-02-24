"""
.well-known URL patterns for ActivityPub discovery.
"""

from django.urls import path

from . import views

urlpatterns = [
    path("webfinger", views.webfinger, name="webfinger"),
    path("nodeinfo", views.nodeinfo_index, name="nodeinfo-index"),
    path("nodeinfo/2.0", views.nodeinfo, name="nodeinfo"),
]
