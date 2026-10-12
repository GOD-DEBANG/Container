"""
src/pulse/fabric/coalescing.py

SingleFlight request coalescing.
Suppresses duplicate in-flight concurrent read requests for identical keys,
sharing one execution result among all awaiting callers.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine, Dict


class RequestCoalescer:
    def __init__(self) -> None:
        # key -> asyncio.Future
        self._in_flight: Dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()

    async def execute(self, key: str, loader_fn: Callable[[], Coroutine[Any, Any, Any]]) -> Any:
        """
        Execute loader_fn for key, or join an already in-flight request for the same key.
        """
        async with self._lock:
            if key in self._in_flight:
                future = self._in_flight[key]
                join_existing = True
            else:
                loop = asyncio.get_running_loop()
                future = loop.create_future()
                self._in_flight[key] = future
                join_existing = False

        if join_existing:
            return await future

        # Leader executes the loader
        try:
            result = await loader_fn()
            future.set_result(result)
            return result
        except BaseException as exc:
            future.set_exception(exc)
            raise
        finally:
            async with self._lock:
                self._in_flight.pop(key, None)
