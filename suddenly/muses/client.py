"""MusesClient — thin HTTP boundary to the suddenly-muses hub (#76).

The hub lives at ``SUDDENLY_MUSES_URL`` (production: https://muse.suddenly.social)
and exposes two families of calls:

* ``analyze``  — projection of one or more labelled corpora onto the hub's
  pattern tables. Used for the ingestion summary (#83), federated link
  suggestions (#84) and claim-coherence analysis (#128).
* ``suggest``  — a best-of-N narrative suggestion from a ``SessionContext``.
  Used for the shared-sequence opening (#127) and the standard inline
  description/narration suggestions (#79).

Design contract:

* The client never crashes the host flow. On disabled/unconfigured/unreachable
  hub it raises :class:`MusesUnavailable`; on a broken request/response it
  raises :class:`MusesContractError`. Both derive from ``MusesError`` so a
  single ``except MusesError`` gives the degraded-mode behaviour (#88).
* No editorial logic lives here — the client only serialises context, signs
  the request and maps transport errors. Interpreting the returned dict is the
  caller's job (each feature knows its own response shape).
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any

from django.conf import settings

from .exceptions import MusesContractError, MusesUnavailable

logger = logging.getLogger("suddenly.muses")

# API surface on the hub. Versioned so the instance and hub can evolve
# independently; kept here (not in settings) because it is part of the client
# contract, not a deployment knob.
_ANALYZE_PATH = "/api/v1/analyze"
_SUGGEST_PATH = "/api/v1/suggest"


@dataclass
class Corpus:
    """One labelled body of text handed to ``analyze``.

    ``label`` distinguishes the corpora in a multi-corpus call (e.g. ``"npc"``
    vs ``"candidate_pc"`` for claim coherence, #128).
    """

    label: str
    content: str
    tags: list[str] = field(default_factory=list)


@dataclass
class SessionContext:
    """Context for a ``suggest`` call.

    ``characters`` is a list of character-sheet dicts. The base ``suggest``
    (#79) carries a single sheet; the shared-sequence opening (#127) carries
    two plus a ``link_type``. ``kind`` optionally constrains the returned
    suggestion (e.g. never ``dialogue`` in a shared sequence, #127).
    """

    characters: list[dict[str, Any]] = field(default_factory=list)
    link_type: str | None = None
    reports: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    kind: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        # Drop empty optionals so the wire stays tidy and the hub can apply
        # its own defaults.
        return {k: v for k, v in payload.items() if v not in (None, [], "")}


class MusesClient:
    """HTTP client for the Muses hub. Instantiate per call; it is cheap."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.base_url = str(base_url or getattr(settings, "SUDDENLY_MUSES_URL", "") or "").rstrip(
            "/"
        )
        self.api_key = str(api_key or getattr(settings, "SUDDENLY_MUSES_API_KEY", "") or "")
        self.timeout = timeout or float(getattr(settings, "SUDDENLY_MUSES_TIMEOUT", 30))

    # -- availability ------------------------------------------------------

    @staticmethod
    def is_enabled() -> bool:
        """True only if the feature flag is on *and* the hub is configured.

        Callers can short-circuit on this before assembling an expensive
        context, but every request also re-checks, so it is only an optimisation.
        """
        if not getattr(settings, "SUDDENLY_MUSES_ENABLED", False):
            return False
        return bool(getattr(settings, "SUDDENLY_MUSES_URL", "")) and bool(
            getattr(settings, "SUDDENLY_MUSES_API_KEY", "")
        )

    # -- public API --------------------------------------------------------

    def analyze(
        self,
        *,
        feature: str,
        content: str | None = None,
        tags: list[str] | None = None,
        corpora: list[Corpus] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run an ``analyze`` feature on the hub.

        Pass either ``content`` (+ optional ``tags``) for a single-corpus
        analysis, or ``corpora`` for a multi-corpus one (claim coherence).
        ``feature`` names the hub analysis, e.g. ``"summary"``,
        ``"federated_links"``, ``"claim_coherence"``.
        """
        body: dict[str, Any] = {"feature": feature}
        if corpora is not None:
            body["corpora"] = [asdict(c) for c in corpora]
        if content is not None:
            body["content"] = content
        if tags:
            body["tags"] = tags
        if extra:
            body.update(extra)
        return self._post(_ANALYZE_PATH, body)

    def suggest(self, context: SessionContext, *, feature: str = "opening") -> dict[str, Any]:
        """Request a best-of-N narrative suggestion for ``context``."""
        body: dict[str, Any] = {"feature": feature, **context.to_payload()}
        return self._post(_SUGGEST_PATH, body)

    # -- transport ---------------------------------------------------------

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        if not self.is_enabled():
            raise MusesUnavailable("Muses is disabled or unconfigured on this instance.")

        import httpx  # local import: httpx is a federation optional-extra

        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=body, headers=headers)
        except httpx.RequestError as exc:
            logger.warning("Muses request failed (%s): %s", path, exc)
            raise MusesUnavailable(f"Muses hub unreachable: {exc}") from exc

        if response.status_code >= 500:
            logger.warning("Muses hub 5xx (%s): %s", path, response.status_code)
            raise MusesUnavailable(f"Muses hub returned {response.status_code}.")
        if response.status_code >= 400:
            logger.error(
                "Muses hub 4xx (%s): %s %s", path, response.status_code, response.text[:500]
            )
            raise MusesContractError(f"Muses hub rejected the request ({response.status_code}).")

        try:
            data: dict[str, Any] = response.json()
        except ValueError as exc:
            raise MusesContractError("Muses hub returned a non-JSON body.") from exc
        if not isinstance(data, dict):
            raise MusesContractError("Muses hub returned an unexpected payload shape.")
        return data
