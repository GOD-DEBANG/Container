"""
src/pulse/cells/error_cell.py

Error Normalization Cell.
Converts exceptions into standardized error Pulse instances with status codes.
"""

from __future__ import annotations

from ..core.pipeline import BaseCell, PulseContext
from ..core.pulse import Pulse


class ErrorNormalizationCell(BaseCell):
    name = "ErrorNormalizationCell"
    input_contract = Pulse
    output_contract = Pulse

    async def process(self, context: PulseContext) -> PulseContext:
        if context.error is not None:
            err = context.error
            status_code = getattr(err, "status_code", 500)
            error_code = getattr(err, "error_code", "INTERNAL_ERROR")
            details = getattr(err, "details", {})

            error_pulse = Pulse.create(
                event_type="pulse_error",
                payload={
                    "error": True,
                    "status_code": status_code,
                    "error_code": error_code,
                    "message": str(err.message if hasattr(err, "message") else err),
                    "details": details,
                },
                request_id=context.current_pulse.request_id,
                job_id=context.current_pulse.job_id,
                correlation_id=context.current_pulse.correlation_id,
                trace_id=context.current_pulse.trace_id,
            )
            context.response_pulse = error_pulse
        return context
