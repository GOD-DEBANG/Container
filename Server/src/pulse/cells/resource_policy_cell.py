"""
src/pulse/cells/resource_policy_cell.py

Resource Policy Cell.
Enforces execution bounds and serverless timeout safety limits.
"""

from __future__ import annotations

from ..core.pipeline import BaseCell, PulseContext
from ..core.pulse import Pulse
from ..flow_control.admission import ServerAdmissionController


class ResourcePolicyCell(BaseCell):
    name = "ResourcePolicyCell"
    input_contract = Pulse
    output_contract = Pulse

    def __init__(self, max_inline_bytes: int = 268435456) -> None:
        self.max_inline_bytes = max_inline_bytes

    async def process(self, context: PulseContext) -> PulseContext:
        params = context.state.get("validated_params", {})
        target_size = params.get("target_size_bytes", 0)
        backend = params.get("backend", "INLINE")

        # Admission validation
        ServerAdmissionController.validate_dataset_job_parameters(
            target_size_bytes=target_size,
            backend=backend,
            max_inline_bytes=self.max_inline_bytes,
        )

        context.state["policy_approved"] = True
        return context
