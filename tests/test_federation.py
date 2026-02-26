"""
Contract tests for FederatedServer model.
"""

import pytest
from django.db import IntegrityError

from suddenly.activitypub.models import FederatedServer, ServerStatus


class TestFederatedServerStr:
    """__str__ returns the domain name."""

    def test_str_returns_server_name(self, db):
        server = FederatedServer.objects.create(server_name="mastodon.social")
        assert str(server) == "mastodon.social"


class TestFederatedServerDefaultStatus:
    """New servers start with UNKNOWN status."""

    def test_default_status_is_unknown(self, db):
        server = FederatedServer.objects.create(server_name="new.instance")
        assert server.status == ServerStatus.UNKNOWN


class TestFederatedServerIsSuddenlyInstance:
    """is_suddenly_instance() identifies Suddenly software by application_type."""

    def test_returns_true_for_suddenly_type(self, db):
        server = FederatedServer.objects.create(
            server_name="soudainement.fr",
            application_type="suddenly",
        )
        assert server.is_suddenly_instance() is True

    def test_returns_false_for_other_type(self, db):
        server = FederatedServer.objects.create(
            server_name="mastodon.social",
            application_type="mastodon",
        )
        assert server.is_suddenly_instance() is False

    def test_returns_false_when_type_empty(self, db):
        server = FederatedServer.objects.create(server_name="unknown.social")
        assert server.is_suddenly_instance() is False


class TestFederatedServerUniqueness:
    """server_name is a unique natural key."""

    def test_duplicate_server_name_raises(self, db):
        FederatedServer.objects.create(server_name="example.social")
        with pytest.raises(IntegrityError):
            FederatedServer.objects.create(server_name="example.social")
