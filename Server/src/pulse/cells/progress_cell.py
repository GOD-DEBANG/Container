"""
src/pulse/cells/progress_cell.py

Progress Event Creation Cell.
Constructs typed progress pulses for streaming delivery.
"""

from __future__ import annotations

from ..core.pipeline import BaseCell, PulseContext
from ..core.pulse import Pulse


class ProgressCell(BaseCell):
    name = "ProgressCell"
    input_contract = Pulse
    output_contract = Pulse

    async def process(self, context: PulseContext) -> PulseContext:
        pulse = context.current_pulse
        job_id = pulse.job_id or context.state.get("job_id", "")
        progress_data = context.state.get("progress_event_data", {})

        progress_pulse = Pulse.create(
            event_type="pulse_progress",
            payload=progress_data,
            job_id=job_id,
            principal_id=pulse.principal_id,
            correlation_id=pulse.correlation_id,
            trace_id=pulse.trace_id,
        )

        context.current_pulse = progress_pulse
        return context
