from django.urls import path

from . import views

app_name = "docs"

urlpatterns = [
    path("", views.index, name="index"),
    path("w/<str:name>/", views.wireframe_prototype, name="wireframe_prototype"),
    path("<str:section>/<str:slug>/", views.page, name="page"),
]
