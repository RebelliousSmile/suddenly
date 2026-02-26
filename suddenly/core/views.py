"""
Core views.
"""

from django.shortcuts import render


def home(request):
    """Home page."""
    return render(request, "core/home.html")
