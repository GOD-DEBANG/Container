"""
src/vdc/layer2_processing/bounded_queue.py

Thread-safe bounded queue applying backpressure when memory limits are reached.
"""

from __future__ import annotations

import queue
from typing import Generic, TypeVar, Optional

T = TypeVar("T")


class BoundedWorkQueue(Generic[T]):
    def __init__(self, maxsize: int = 16) -> None:
        if maxsize <= 0:
            raise ValueError(f"maxsize must be positive, got {maxsize}")
        self._queue: queue.Queue[T] = queue.Queue(maxsize=maxsize)
        self._maxsize = maxsize

    @property
    def maxsize(self) -> int:
        return self._maxsize

    def qsize(self) -> int:
        return self._queue.qsize()

    def is_full(self) -> bool:
        return self._queue.full()

    def put(self, item: T, timeout: Optional[float] = None) -> bool:
        """
        Put an item into the queue. Blocks if full until space is available or timeout expires.
        Returns True on success, False if timed out (backpressure applied).
        """
        try:
            self._queue.put(item, block=True, timeout=timeout)
            return True
        except queue.Full:
            return False

    def get(self, timeout: Optional[float] = None) -> Optional[T]:
        """
        Get an item from the queue. Returns None if timed out.
        """
        try:
            return self._queue.get(block=True, timeout=timeout)
        except queue.Empty:
            return None

    def task_done(self) -> None:
        self._queue.task_done()
