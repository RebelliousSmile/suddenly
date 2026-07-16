"""Unit tests for fediverse_auth.client (remote calls mocked)."""

from __future__ import annotations

from suddenly.fediverse_auth import client

# Real-world NodeInfo discovery payload (Mastodon): the rel is the diaspora
# schema URI — it ends with "schema/2.0", NOT "nodeinfo/2.0".
NODEINFO_INDEX = {
    "links": [
        {
            "rel": "http://nodeinfo.diaspora.software/ns/schema/2.0",
            "href": "https://toot.example/nodeinfo/2.0",
        }
    ]
}

NODEINFO_DOCUMENT = {"software": {"name": "Mastodon", "version": "4.3.1"}}


class TestDetectSoftware:
    def test_resolves_standard_diaspora_rel(self, mocker) -> None:
        get = mocker.patch.object(client, "_get", side_effect=[NODEINFO_INDEX, NODEINFO_DOCUMENT])
        assert client.detect_software("toot.example") == "mastodon"
        assert get.call_args_list[1].args == ("https://toot.example/nodeinfo/2.0",)

    def test_matches_newer_schema_versions(self, mocker) -> None:
        index = {
            "links": [
                {
                    "rel": "http://nodeinfo.diaspora.software/ns/schema/2.1",
                    "href": "https://toot.example/nodeinfo/2.1",
                }
            ]
        }
        mocker.patch.object(client, "_get", side_effect=[index, NODEINFO_DOCUMENT])
        assert client.detect_software("toot.example") == "mastodon"

    def test_unknown_rel_returns_empty(self, mocker) -> None:
        mocker.patch.object(client, "_get", return_value={"links": [{"rel": "other", "href": "x"}]})
        assert client.detect_software("toot.example") == ""

    def test_network_failure_returns_empty(self, mocker) -> None:
        mocker.patch.object(client, "_get", side_effect=client.FediverseClientError("boom"))
        assert client.detect_software("toot.example") == ""


class TestBaseUrl:
    def test_always_https(self, settings) -> None:
        # AP_ALLOW_INSECURE_HTTP tolerates inbound http URLs; it must never
        # downgrade our own outbound OAuth calls (real instances 301 to https).
        settings.AP_ALLOW_INSECURE_HTTP = True
        assert client._base_url("mastodon.social") == "https://mastodon.social"
