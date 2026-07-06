"""
Shared URL helpers for ActivityPub serialization.
"""

from __future__ import annotations

import mimetypes

from django.conf import settings
from django.db.models.fields.files import FieldFile


def absolute_media_url(file_field: FieldFile) -> str:
    """
    Return an absolute URL for a FileField/ImageField, regardless of storage backend.

    S3Storage/R2 already returns an absolute URL from `.url`; FileSystemStorage
    returns a relative path that must be prefixed with the instance domain.
    """
    url: str = file_field.url
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"https://{settings.DOMAIN}{url}"


def media_type_for_file(file_field: FieldFile) -> str:
    """
    Return the MIME type for a FileField/ImageField, derived from its filename.

    Falls back to "application/octet-stream" if the type cannot be guessed
    from the extension (e.g. no extension, or an unrecognized one).
    """
    name = file_field.name
    if not name:
        return "application/octet-stream"
    content_type, _encoding = mimetypes.guess_type(name)
    return content_type or "application/octet-stream"
