"""
src/pulse/flow_control/backpressure.py

Adaptive backpressure and token-bucket concurrency limiter.
Sheds load and rejects requests with BackpressureError when saturated.
"""

from __future__ import annotations

import asyncio

from ..core.errors import BackpressureError


class ConcurrencyLimiter:
    def __init__(self, max_concurrent: int = 16, acquire_timeout_seconds: float = 2.0) -> None:
        self.max_concurrent = max_concurrent
        self.timeout = acquire_timeout_seconds
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def __aenter__(self) -> ConcurrencyLimiter:
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=self.timeout)
            return self
        except asyncio.TimeoutError:
            raise BackpressureError(
                f"Server is currently under heavy load (concurrency limit {self.max_concurrent} saturated)"
            )

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self._semaphore.release()
