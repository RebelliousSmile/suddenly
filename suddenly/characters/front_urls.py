"""
Front-end URL patterns for characters (DA-1: HTMX-first).

These serve HTML pages. The DRF API URLs remain in api_urls.py.
"""

from django.urls import path

from . import front_views, gm_views, link_views, sequence_views

app_name = "characters"

urlpatterns = [
    path("", front_views.character_list, name="list"),
    path("search/", front_views.character_search, name="search"),
    path("dashboard/", gm_views.gm_dashboard, name="gm_dashboard"),
    # Link requests management
    path("requests/", link_views.link_requests_list, name="link_requests"),
    path(
        "requests/<uuid:pk>/accept/",
        link_views.link_request_accept,
        name="link_request_accept",
    ),
    path(
        "requests/<uuid:pk>/reject/",
        link_views.link_request_reject,
        name="link_request_reject",
    ),
    path(
        "requests/<uuid:pk>/cancel/",
        link_views.link_request_cancel,
        name="link_request_cancel",
    ),
    # SharedSequence editor
    path(
        "sequences/<uuid:pk>/",
        sequence_views.sequence_edit,
        name="sequence_edit",
    ),
    path(
        "sequences/<uuid:pk>/propose/",
        sequence_views.sequence_propose_publish,
        name="sequence_propose",
    ),
    path(
        "sequences/<uuid:pk>/publish/",
        sequence_views.sequence_validate_publish,
        name="sequence_publish",
    ),
    # Character detail + actions
    path("<slug:slug>/", front_views.character_detail, name="detail"),
    path("<slug:slug>/quotes/add/", front_views.quote_add, name="quote_add"),
    path("<slug:slug>/link/", link_views.link_choose_type, name="link_choose"),
    path(
        "<slug:slug>/link/<str:link_type>/",
        link_views.link_request_form,
        name="link_request_form",
    ),
]
