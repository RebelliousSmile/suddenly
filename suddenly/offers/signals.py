"""
Django signals for the offers app.

Phase 1 (this file): import hook only, so ``OffersConfig.ready()`` has
something to wire. Phase 2 adds expiration receivers (DEC-B3) on the 3
carrier models; Phase 3 adds follower-notification receivers (DEC-B5).
"""

from __future__ import annotations
