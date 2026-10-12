"""
src/pulse/fabric/l1_cache.py

Thread-safe in-memory L1 cache with LRU eviction and per-item TTL expiration.
"""

from __future__ import annotations

import collections
import threading
import time
from typing import Any, Optional, Tuple


class L1Cache:
    def __init__(self, capacity: int = 1000, default_ttl_seconds: float = 60.0) -> None:
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")
        self.capacity = capacity
        self.default_ttl = default_ttl_seconds
        # key -> (value, expiry_timestamp)
        self._store: collections.OrderedDict[str, Tuple[Any, float]] = collections.OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._store:
                return None
            val, exp = self._store[key]
            if time.time() > exp:
                del self._store[key]
                return None
            # Move to end (most recently accessed)
            self._store.move_to_end(key)
            return val

    def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expiry = time.time() + ttl
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = (value, expiry)
            if len(self._store) > self.capacity:
                self._store.popitem(last=False)  # Evict oldest LRU

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
