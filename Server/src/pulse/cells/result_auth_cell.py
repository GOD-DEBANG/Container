"""
src/pulse/cells/result_auth_cell.py

Result Authorization Cell.
Enforces that callers can only access dataset job results they own.
"""

from __future__ import annotations

from ..core.pipeline import BaseCell, PulseContext
from ..core.pulse import Pulse
from ..core.errors import AuthorizationError, JobNotFoundError
from ..fabric.store_interface import StoreInterface


class ResultAuthCell(BaseCell):
    name = "ResultAuthCell"
    input_contract = Pulse
    output_contract = Pulse

    def __init__(self, store: StoreInterface) -> None:
        self.store = store

    async def process(self, context: PulseContext) -> PulseContext:
        pulse = context.current_pulse
        job_id = context.state.get("target_job_id") or pulse.job_id

        if not job_id:
            raise JobNotFoundError("No target job_id specified for result authorization")

        job_data = await self.store.get_job(job_id)
        if not job_data:
            raise JobNotFoundError(f"Job with ID '{job_id}' not found")

        caller_principal = pulse.principal_id or context.state.get("principal_id")
        owner_principal = job_data.get("principal_id")

        # Allow if caller is owner or if principal matches admin/system
        if owner_principal and caller_principal != owner_principal and caller_principal != "admin":
            raise AuthorizationError(
                f"Principal '{caller_principal}' is not authorized to access job '{job_id}' owned by '{owner_principal}'"
            )

        context.state["authorized_job_data"] = job_data
        return context
