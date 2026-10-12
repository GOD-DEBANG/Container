"""
src/pulse/cells/job_creation_cell.py

Dataset Job Creation Cell.
Assigns a unique job_id and registers the job within the State Fabric.
"""

from __future__ import annotations

import time
import uuid

from ..core.pipeline import BaseCell, PulseContext
from ..core.pulse import Pulse
from ..fabric.store_interface import StoreInterface


class JobCreationCell(BaseCell):
    name = "JobCreationCell"
    input_contract = Pulse
    output_contract = Pulse

    def __init__(self, store: StoreInterface) -> None:
        self.store = store

    async def process(self, context: PulseContext) -> PulseContext:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        params = context.state.get("validated_params", {})
        principal_id = context.state.get("principal_id", "anonymous")

        job_record = {
            "job_id": job_id,
            "principal_id": principal_id,
            "status": "QUEUED",
            "params": params,
            "created_at_utc": time.time(),
            "updated_at_utc": time.time(),
        }

        await self.store.save_job(job_id, job_record)

        # Update current pulse with job_id
        context.current_pulse = context.current_pulse.with_job(job_id)
        context.state["job_id"] = job_id
        context.state["job_record"] = job_record
        return context
