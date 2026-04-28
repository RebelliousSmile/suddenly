"""
Tests for locale-specific date and number formatting.
"""

from __future__ import annotations

import datetime

import pytest
from django.utils import formats, translation


class TestDateFormatFrench:
    def test_date_format_french(self) -> None:
        date = datetime.date(2026, 4, 28)
        with translation.override("fr"):
            formatted = formats.date_format(date, "j F Y")
        assert formatted == "28 avril 2026"

    def test_month_name_french(self) -> None:
        date = datetime.date(2026, 1, 15)
        with translation.override("fr"):
            formatted = formats.date_format(date, "F")
        assert formatted == "janvier"


class TestDateFormatEnglish:
    def test_date_format_english(self) -> None:
        date = datetime.date(2026, 4, 28)
        with translation.override("en"):
            formatted = formats.date_format(date, "F j, Y")
        assert formatted == "April 28, 2026"

    def test_month_name_english(self) -> None:
        date = datetime.date(2026, 1, 15)
        with translation.override("en"):
            formatted = formats.date_format(date, "F")
        assert formatted == "January"
