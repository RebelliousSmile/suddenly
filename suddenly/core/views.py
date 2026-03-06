"""
Core views.
"""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def home(request: HttpRequest) -> HttpResponse:
    """Home page."""
    return render(request, "core/home.html")
