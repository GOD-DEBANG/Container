"""
src/pulse/fabric/store_interface.py

Typed abstract state store interface for PULSE.
Decouples job tracking and event persistence from specific backend storage technology.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class StoreInterface(ABC):
    @abstractmethod
    async def save_job(self, job_id: str, job_data: Dict[str, Any]) -> None:
        """Persist or update job metadata."""
        pass

    @abstractmethod
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve job metadata by job_id."""
        pass

    @abstractmethod
    async def append_event(self, job_id: str, event_data: Dict[str, Any]) -> int:
        """
        Append an event to the job's durable event stream.
        Returns the assigned monotonic sequence number / cursor.
        """
        pass

    @abstractmethod
    async def get_events_since(self, job_id: str, cursor: int = 0) -> List[Dict[str, Any]]:
        """Retrieve all events for job_id with sequence > cursor."""
        pass
