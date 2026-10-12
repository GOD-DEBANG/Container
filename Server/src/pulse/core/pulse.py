"""
src/pulse/core/pulse.py

Immutable typed request and lifecycle event model: Pulse.
Every accepted request becomes a typed Pulse instance.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class Pulse:
    """
    Typed, immutable event representation.
    """
    pulse_id: str
    request_id: str
    schema_version: str
    event_type: str
    created_at_utc: float
    correlation_id: str
    trace_id: str
    payload: Dict[str, Any]
    integrity_metadata: Dict[str, Any] = field(default_factory=dict)
    principal_id: Optional[str] = None
    job_id: Optional[str] = None

    @classmethod
    def create(
        cls,
        event_type: str,
        payload: Dict[str, Any],
        request_id: Optional[str] = None,
        job_id: Optional[str] = None,
        principal_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        integrity_metadata: Optional[Dict[str, Any]] = None,
        schema_version: str = "1.0",
    ) -> Pulse:
        req_id = request_id or f"req_{uuid.uuid4().hex[:12]}"
        corr_id = correlation_id or req_id
        trc_id = trace_id or f"trc_{uuid.uuid4().hex[:12]}"

        return cls(
            pulse_id=f"pls_{uuid.uuid4().hex[:12]}",
            request_id=req_id,
            job_id=job_id,
            schema_version=schema_version,
            event_type=event_type,
            created_at_utc=time.time(),
            principal_id=principal_id,
            payload=dict(payload),
            integrity_metadata=dict(integrity_metadata or {}),
            correlation_id=corr_id,
            trace_id=trc_id,
        )

    def with_principal(self, principal_id: str) -> Pulse:
        """Derive a new Pulse with authenticated principal."""
        return Pulse(
            pulse_id=self.pulse_id,
            request_id=self.request_id,
            schema_version=self.schema_version,
            event_type=self.event_type,
            created_at_utc=self.created_at_utc,
            correlation_id=self.correlation_id,
            trace_id=self.trace_id,
            payload=self.payload,
            integrity_metadata=self.integrity_metadata,
            principal_id=principal_id,
            job_id=self.job_id,
        )

    def with_job(self, job_id: str) -> Pulse:
        """Derive a new Pulse with assigned job_id."""
        return Pulse(
            pulse_id=self.pulse_id,
            request_id=self.request_id,
            schema_version=self.schema_version,
            event_type=self.event_type,
            created_at_utc=self.created_at_utc,
            correlation_id=self.correlation_id,
            trace_id=self.trace_id,
            payload=self.payload,
            integrity_metadata=self.integrity_metadata,
            principal_id=self.principal_id,
            job_id=job_id,
        )
