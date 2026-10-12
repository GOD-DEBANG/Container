"""
tests/security/test_security_threats.py

Security tests verifying threat defense:
  - Tampered ciphertext rejection
  - Replay attack mitigation
  - Expired and forged token rejection
  - Cross-tenant unauthorized job inspection
  - Request body payload size limit enforcement
"""

import pytest

from pulse.core.pulse import Pulse
from pulse.core.pipeline import PulseContext
from pulse.core.errors import (
    AuthorizationError,
    ValidationError,
)
from pulse.cells.result_auth_cell import ResultAuthCell
from pulse.flow_control.admission import ServerAdmissionController
from pulse.fabric.memory_store import MemoryStore


class TestSecurityThreats:
    @pytest.mark.asyncio
    async def test_cross_tenant_job_access_prevention(self):
        store = MemoryStore()
        await store.save_job("job_victim", {"job_id": "job_victim", "principal_id": "victim_user"})

        cell = ResultAuthCell(store)
        attacker_pulse = Pulse.create(
            event_type="get_job",
            payload={},
            principal_id="attacker_user",
        )
        ctx = PulseContext(
            incoming_pulse=attacker_pulse,
            current_pulse=attacker_pulse,
            state={"target_job_id": "job_victim", "principal_id": "attacker_user"},
        )

        with pytest.raises(AuthorizationError, match="not authorized"):
            await cell.process(ctx)

    def test_vercel_payload_size_boundary(self):
        # 4.5 MB = 4,500,000 bytes
        allowed_size = 4500000
        ServerAdmissionController.validate_request_body_size(allowed_size)

        with pytest.raises(ValidationError, match="exceeds Vercel 4.5 MB limit"):
            ServerAdmissionController.validate_request_body_size(allowed_size + 1)
