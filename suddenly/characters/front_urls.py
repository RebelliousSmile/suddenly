"""
Front-end URL patterns for characters (DA-1: HTMX-first).

These serve HTML pages. The DRF API URLs remain in api_urls.py.
"""

from django.urls import path

from . import (
    follow_views,
    front_views,
    gm_views,
    link_views,
    sequence_views,
    trait_views,
)

app_name = "characters"

urlpatterns = [
    path("", front_views.character_list, name="list"),
    path("search/", front_views.character_search, name="search"),
    path("dashboard/", gm_views.gm_dashboard, name="gm_dashboard"),
    path("follow/", follow_views.follow_toggle, name="follow_toggle"),
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
    path(
        "requests/<uuid:pk>/card/",
        link_views.link_request_card_partial,
        name="link_request_card_partial",
    ),
    # Link revocation (US-16)
    path("links/<uuid:pk>/revoke/", link_views.link_revoke, name="link_revoke"),
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
    path("bulk-delete/", front_views.character_delete_bulk, name="delete_bulk"),
    # Character detail + actions
    path("<slug:slug>/", front_views.character_detail, name="detail"),
    path("<slug:slug>/edit/", front_views.character_edit, name="edit"),
    path("<slug:slug>/delete/", front_views.character_delete, name="delete"),
    path("<slug:slug>/quotes/add/", front_views.quote_add, name="quote_add"),
    path("<slug:slug>/card/", front_views.character_card, name="card"),
    # Narrative meta-model editor (issue B) — traits & actions
    path("<slug:slug>/traits/", trait_views.traits_editor, name="traits_editor"),
    path(
        "<slug:slug>/traits/sets/add/",
        trait_views.trait_set_create,
        name="trait_set_create",
    ),
    path(
        "<slug:slug>/traits/sets/<uuid:set_pk>/delete/",
        trait_views.trait_set_delete,
        name="trait_set_delete",
    ),
    path(
        "<slug:slug>/traits/sets/<uuid:set_pk>/traits/add/",
        trait_views.trait_create,
        name="trait_create",
    ),
    path(
        "<slug:slug>/traits/traits/<uuid:trait_pk>/delete/",
        trait_views.trait_delete,
        name="trait_delete",
    ),
    path(
        "<slug:slug>/traits/sets/<uuid:set_pk>/actions/add/",
        trait_views.action_create,
        name="action_create",
    ),
    path(
        "<slug:slug>/traits/actions/<uuid:action_pk>/delete/",
        trait_views.action_delete,
        name="action_delete",
    ),
    path("<slug:slug>/link/", link_views.link_choose_type, name="link_choose"),
    path(
        "<slug:slug>/link/<str:link_type>/",
        link_views.link_request_form,
        name="link_request_form",
    ),
]
