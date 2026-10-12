"""
src/pulse/streams/event_buffer.py

Bounded ring buffer for streaming events.
Retains a fixed window of recent events per job to allow instant replay
upon client disconnect and cursor reconnection.
"""

from __future__ import annotations

import collections
import threading
from typing import Any, Dict, List


class EventBuffer:
    def __init__(self, capacity_per_job: int = 500) -> None:
        self.capacity = capacity_per_job
        # job_id -> deque of event dicts
        self._buffers: Dict[str, collections.deque[Dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def append(self, job_id: str, event_data: Dict[str, Any]) -> None:
        with self._lock:
            if job_id not in self._buffers:
                self._buffers[job_id] = collections.deque(maxlen=self.capacity)
            self._buffers[job_id].append(dict(event_data))

    def get_since(self, job_id: str, cursor: int) -> List[Dict[str, Any]]:
        with self._lock:
            if job_id not in self._buffers:
                return []
            return [e for e in self._buffers[job_id] if e.get("cursor", 0) > cursor]

    def clear(self, job_id: str) -> None:
        with self._lock:
            self._buffers.pop(job_id, None)
