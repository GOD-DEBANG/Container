"""
src/pulse/cells/resource_policy_cell.py

Resource Policy Cell.
Enforces execution bounds and serverless timeout safety limits.
"""

from __future__ import annotations

from typing import Optional

from ..core.pipeline import BaseCell, PulseContext
from ..core.pulse import Pulse
from ..core.errors import PulseError
from ..flow_control.admission import ServerAdmissionController


class ResourcePolicyCell(BaseCell):
    name = "ResourcePolicyCell"
    input_contract = Pulse
    output_contract = Pulse

    def __init__(
        self,
        max_inline_bytes: int = 268435456,
        allowed_backend: Optional[str] = None,
    ) -> None:
        self.max_inline_bytes = max_inline_bytes
        # When set, only this backend may be requested (enforces VDC_EXECUTION_BACKEND).
        # None means any validated backend is permitted.
        self.allowed_backend = allowed_backend.upper() if allowed_backend else None

    async def process(self, context: PulseContext) -> PulseContext:
        params = context.state.get("validated_params", {})
        target_size = params.get("target_size_bytes", 0)
        backend = params.get("backend", "INLINE")

        # Enforce server-level backend restriction from VDC_EXECUTION_BACKEND config.
        if self.allowed_backend and backend != self.allowed_backend:
            raise PulseError(
                f"Backend '{backend}' is not permitted on this server. "
                f"This server is configured for '{self.allowed_backend}' only.",
                details={"status_code": 400, "requested_backend": backend, "allowed_backend": self.allowed_backend},
            )

        # Admission validation
        ServerAdmissionController.validate_dataset_job_parameters(
            target_size_bytes=target_size,
            backend=backend,
            max_inline_bytes=self.max_inline_bytes,
        )

        context.state["policy_approved"] = True
        return context
