"""
src/pulse/security/replay_guard.py

Bounded sliding window replay guard.
Enforces nonce freshness, timestamp drift tolerance, and duplicate rejection.
"""

from __future__ import annotations

import time
from typing import Dict

from ..core.errors import ReplayAttackError


class ReplayGuard:
    def __init__(self, window_seconds: float = 60.0, max_cached_nonces: int = 10000) -> None:
        self.window_seconds = window_seconds
        self.max_cached = max_cached_nonces
        # Map of nonce -> expiry timestamp
        self._seen_nonces: Dict[str, float] = {}

    def _evict_stale(self, now: float) -> None:
        stale = [nonce for nonce, exp in self._seen_nonces.items() if exp < now]
        for s in stale:
            del self._seen_nonces[s]

    def validate_and_record(self, nonce: str, timestamp_utc: float) -> None:
        """
        Validate nonce and timestamp.
        Raises ReplayAttackError on duplicate nonce or out-of-window timestamp.
        """
        now = time.time()
        # Evict periodically
        if len(self._seen_nonces) > self.max_cached or (len(self._seen_nonces) % 100 == 0):
            self._evict_stale(now)

        # Check timestamp drift
        drift = abs(now - timestamp_utc)
        if drift > self.window_seconds:
            raise ReplayAttackError(
                f"Request timestamp drift ({drift:.2f}s) exceeds allowable window ({self.window_seconds}s)"
            )

        if nonce in self._seen_nonces:
            raise ReplayAttackError(f"Duplicate nonce detected (replay attack): {nonce}")

        # Store until timestamp + window
        self._seen_nonces[nonce] = timestamp_utc + self.window_seconds
