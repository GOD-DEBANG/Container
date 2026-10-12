"""
src/pulse/streams/sse.py

Server-Sent Events (SSE) generator and formatting protocol.
Implements event IDs, event type names, JSON payloads, keepalive heartbeats,
and cursor-based replay.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator, Optional

from ..fabric.store_interface import StoreInterface


class SSEStreamer:
    @staticmethod
    def format_sse_event(event_type: str, data: Any, event_id: Optional[str | int] = None) -> str:
        """Format an SSE message block adhering to W3C SSE standard."""
        lines: list[str] = []
        if event_id is not None:
            lines.append(f"id: {event_id}")
        lines.append(f"event: {event_type}")
        
        # Serialize data to JSON string
        if isinstance(data, (dict, list, str, int, float, bool)):
            payload_str = json.dumps(data) if not isinstance(data, str) else data
        else:
            payload_str = str(data)

        # Handle multiline data if present
        for line in payload_str.split("\n"):
            lines.append(f"data: {line}")
        lines.append("")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def format_heartbeat() -> str:
        return ": ping\n\n"

    @classmethod
    async def stream_job_events(
        cls,
        job_id: str,
        store: StoreInterface,
        last_event_id: int = 0,
        poll_interval_seconds: float = 0.5,
        heartbeat_interval_seconds: float = 15.0,
        max_duration_seconds: float = 120.0,
    ) -> AsyncIterator[str]:
        """
        Stream events for a job, resuming from last_event_id if reconnecting.
        Emits heartbeats to keep the connection alive through edge proxies.
        """
        cursor = last_event_id
        start_time = asyncio.get_event_loop().time()
        last_heartbeat = start_time

        while True:
            now = asyncio.get_event_loop().time()
            if (now - start_time) > max_duration_seconds:
                # Close stream peacefully before serverless timeout
                yield cls.format_sse_event("timeout", {"message": "Stream duration reached serverless limit"})
                break

            # Fetch new events
            new_events = await store.get_events_since(job_id, cursor)
            for ev in new_events:
                ev_cursor = ev.get("cursor", cursor + 1)
                ev_type = ev.get("event_type", "pulse_progress")
                yield cls.format_sse_event(event_type=ev_type, data=ev, event_id=ev_cursor)
                cursor = max(cursor, ev_cursor)

                # Check if job reached terminal state
                if ev.get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
                    return

            # Emit heartbeat if needed
            if (now - last_heartbeat) >= heartbeat_interval_seconds:
                yield cls.format_heartbeat()
                last_heartbeat = now

            await asyncio.sleep(poll_interval_seconds)
