"""Exceptions for the Muses client seam.

Callers wanting the degraded-mode behaviour (#88) should catch ``MusesError``
— the base class — so that *any* Muses failure (disabled, unreachable, bad
contract) leaves the host flow (ingestion, editor, claim page) intact and
debits nothing.
"""

from __future__ import annotations


class MusesError(Exception):
    """Base class for every Muses failure. Catch this for degraded mode."""


class MusesUnavailable(MusesError):  # noqa: N818 — reads as a state, not an error variant
    """The hub is disabled by config, unconfigured, or unreachable.

    Raised when ``SUDDENLY_MUSES_ENABLED`` is false, the URL/API key is
    missing, or the request times out / the hub returns a 5xx. This is the
    *expected* failure in a deployment without Muses wired up, and nothing
    should be debited.
    """


class MusesContractError(MusesError):
    """The hub answered but the request or response broke the contract (4xx / malformed).

    Distinct from :class:`MusesUnavailable` so it can be logged as a bug rather
    than a transient outage. Still a ``MusesError``, so degraded-mode callers
    swallow it too.
    """
