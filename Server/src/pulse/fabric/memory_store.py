"""
src/pulse/fabric/memory_store.py

Thread-safe in-memory implementation of StoreInterface for local testing and single-instance runs.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from .store_interface import StoreInterface


class MemoryStore(StoreInterface):
    def __init__(self) -> None:
        self._jobs: Dict[str, Dict[str, Any]] = {}
        # job_id -> list of event dicts
        self._events: Dict[str, List[Dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    async def save_job(self, job_id: str, job_data: Dict[str, Any]) -> None:
        async with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(job_data)
            else:
                self._jobs[job_id] = dict(job_data)

    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    async def append_event(self, job_id: str, event_data: Dict[str, Any]) -> int:
        async with self._lock:
            stream = self._events.setdefault(job_id, [])
            cursor = len(stream) + 1
            record = dict(event_data)
            record["cursor"] = cursor
            stream.append(record)
            return cursor

    async def get_events_since(self, job_id: str, cursor: int = 0) -> List[Dict[str, Any]]:
        async with self._lock:
            stream = self._events.get(job_id, [])
            return [dict(e) for e in stream if e.get("cursor", 0) > cursor]
