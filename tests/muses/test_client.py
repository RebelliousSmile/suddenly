"""Tests for the MusesClient seam (#76) and its degraded-mode contract (#88)."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from django.test import override_settings

from suddenly.muses.client import Corpus, MusesClient, SessionContext
from suddenly.muses.exceptions import MusesContractError, MusesUnavailable

ENABLED = dict(
    SUDDENLY_MUSES_ENABLED=True,
    SUDDENLY_MUSES_URL="https://muse.example.test",
    SUDDENLY_MUSES_API_KEY="secret-token",
)


def _mock_httpx(
    mocker: Any,
    *,
    status_code: int = 200,
    json_body: Any = None,
    request_error: Exception | None = None,
) -> Any:
    mock_client = mocker.MagicMock()
    mock_client.__enter__ = mocker.MagicMock(return_value=mock_client)
    mock_client.__exit__ = mocker.MagicMock(return_value=False)
    if request_error is not None:
        mock_client.post.side_effect = request_error
    else:
        mock_response = mocker.MagicMock()
        mock_response.status_code = status_code
        mock_response.text = "" if json_body is None else str(json_body)
        if isinstance(json_body, ValueError):
            mock_response.json.side_effect = json_body
        else:
            mock_response.json.return_value = json_body
        mock_client.post.return_value = mock_response
    return mocker.patch("httpx.Client", return_value=mock_client)


def test_is_enabled_requires_flag_and_config() -> None:
    with override_settings(
        SUDDENLY_MUSES_ENABLED=False,
        **{k: v for k, v in ENABLED.items() if k != "SUDDENLY_MUSES_ENABLED"},
    ):
        assert MusesClient.is_enabled() is False
    with override_settings(
        SUDDENLY_MUSES_ENABLED=True, SUDDENLY_MUSES_URL="", SUDDENLY_MUSES_API_KEY=""
    ):
        assert MusesClient.is_enabled() is False
    with override_settings(**ENABLED):
        assert MusesClient.is_enabled() is True


@override_settings(SUDDENLY_MUSES_ENABLED=False, SUDDENLY_MUSES_URL="", SUDDENLY_MUSES_API_KEY="")
def test_disabled_raises_unavailable_without_network(mocker: Any) -> None:
    spy = _mock_httpx(mocker, json_body={"summary": "x"})
    with pytest.raises(MusesUnavailable):
        MusesClient().analyze(feature="summary", content="hello")
    spy.assert_not_called()  # never touches the network when disabled


@override_settings(**ENABLED)
def test_analyze_single_corpus_success(mocker: Any) -> None:
    _mock_httpx(mocker, json_body={"summary": "a resolved tale"})
    result = MusesClient().analyze(feature="summary", content="body", tags=["dark"])
    assert result == {"summary": "a resolved tale"}


@override_settings(**ENABLED)
def test_analyze_multi_corpus_sends_labelled_corpora(mocker: Any) -> None:
    spy = _mock_httpx(mocker, json_body={"plausibility": "medium"})
    MusesClient().analyze(
        feature="claim_coherence",
        corpora=[Corpus(label="npc", content="c1"), Corpus(label="candidate_pc", content="c2")],
    )
    _, kwargs = spy.return_value.post.call_args
    sent = kwargs["json"]
    assert sent["feature"] == "claim_coherence"
    assert [c["label"] for c in sent["corpora"]] == ["npc", "candidate_pc"]
    assert kwargs["headers"]["Authorization"] == "Bearer secret-token"


@override_settings(**ENABLED)
def test_suggest_serialises_session_context(mocker: Any) -> None:
    spy = _mock_httpx(mocker, json_body={"kind": "description", "text": "A dim tavern."})
    ctx = SessionContext(
        characters=[{"name": "Ada"}, {"name": "Bo"}],
        link_type="claim",
        kind="description",
    )
    result = MusesClient().suggest(ctx, feature="opening")
    assert result["kind"] == "description"
    sent = spy.return_value.post.call_args.kwargs["json"]
    assert sent["feature"] == "opening"
    assert sent["link_type"] == "claim"
    assert len(sent["characters"]) == 2
    assert "reports" not in sent  # empty optionals dropped


@override_settings(**ENABLED)
def test_5xx_raises_unavailable(mocker: Any) -> None:
    _mock_httpx(mocker, status_code=503, json_body=None)
    with pytest.raises(MusesUnavailable):
        MusesClient().analyze(feature="summary", content="x")


@override_settings(**ENABLED)
def test_4xx_raises_contract_error(mocker: Any) -> None:
    _mock_httpx(mocker, status_code=422, json_body=None)
    with pytest.raises(MusesContractError):
        MusesClient().analyze(feature="summary", content="x")


@override_settings(**ENABLED)
def test_network_error_raises_unavailable(mocker: Any) -> None:
    _mock_httpx(mocker, request_error=httpx.ConnectError("refused"))
    with pytest.raises(MusesUnavailable):
        MusesClient().analyze(feature="summary", content="x")


@override_settings(**ENABLED)
def test_non_json_body_raises_contract_error(mocker: Any) -> None:
    _mock_httpx(mocker, status_code=200, json_body=ValueError("no json"))
    with pytest.raises(MusesContractError):
        MusesClient().analyze(feature="summary", content="x")
