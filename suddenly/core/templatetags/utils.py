"""
General-purpose template filters for Suddenly.
"""

from __future__ import annotations

from urllib.parse import urlparse

from django import template

register = template.Library()


@register.filter
def domain_from_url(value: object) -> str:
    """Extract the hostname (netloc) from a URL string.

    Returns the netloc if present, otherwise returns the original value as a
    string (fallback for malformed or relative URLs).

    Example::

        {{ "https://example.com/rapports/abc"|domain_from_url }}
        {# renders: example.com #}
    """
    return urlparse(str(value)).netloc or str(value)
