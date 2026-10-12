"""
src/pulse/observability/tracer.py

Distributed tracing span abstractions.
Correlates pulses across cells and execution layers.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class TraceSpan:
    name: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    start_time_utc: float = field(default_factory=time.time)
    end_time_utc: Optional[float] = None
    attributes: Dict[str, str] = field(default_factory=dict)

    def finish(self) -> None:
        self.end_time_utc = time.time()

    @property
    def duration_seconds(self) -> float:
        end = self.end_time_utc or time.time()
        return max(0.0, end - self.start_time_utc)


class Tracer:
    @staticmethod
    def start_span(name: str, trace_id: str, parent_span_id: Optional[str] = None) -> TraceSpan:
        return TraceSpan(
            name=name,
            trace_id=trace_id,
            span_id=f"spn_{uuid.uuid4().hex[:12]}",
            parent_span_id=parent_span_id,
        )
