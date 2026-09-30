"""
layer2_processing/bounded_queue.py

Thread-safe bounded queue with backpressure.
Used by WorkerManager to limit concurrent in-flight work.
"""

from __future__ import annotations

import queue
import threading
from typing import Generic, TypeVar

T = TypeVar("T")


class BoundedQueue(Generic[T]):
    """
    A thread-safe queue with a configurable maximum depth.

    When the queue is full, put() blocks (backpressure).
    When the queue is empty, get() blocks.

    This prevents unlimited task accumulation and enforces
    resource-bounded execution.
    """

    def __init__(self, maxsize: int) -> None:
        if maxsize < 1:
            raise ValueError(f"maxsize must be >= 1, got {maxsize}")
        self._q: queue.Queue[T] = queue.Queue(maxsize=maxsize)
        self._lock = threading.Lock()

    def put(self, item: T, timeout: float | None = None) -> None:
        """Put an item. Blocks if full (backpressure)."""
        self._q.put(item, timeout=timeout)

    def get(self, timeout: float | None = None) -> T:
        """Get an item. Blocks if empty."""
        return self._q.get(timeout=timeout)

    def task_done(self) -> None:
        self._q.task_done()

    def join(self) -> None:
        self._q.join()

    @property
    def qsize(self) -> int:
        return self._q.qsize()

    @property
    def full(self) -> bool:
        return self._q.full()

    @property
    def empty(self) -> bool:
        return self._q.empty()

    @property
    def maxsize(self) -> int:
        return self._q.maxsize
