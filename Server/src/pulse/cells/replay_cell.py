"""
src/pulse/cells/replay_cell.py

Replay Protection Cell.
Protects against request replay attacks using sliding window nonce validation.
"""

from __future__ import annotations

from ..core.pipeline import BaseCell, PulseContext
from ..core.pulse import Pulse
from ..core.errors import ReplayAttackError
from ..security.replay_guard import ReplayGuard


class ReplayProtectionCell(BaseCell):
    name = "ReplayProtectionCell"
    input_contract = Pulse
    output_contract = Pulse

    def __init__(self, replay_guard: ReplayGuard) -> None:
        self.replay_guard = replay_guard

    async def process(self, context: PulseContext) -> PulseContext:
        pulse = context.current_pulse
        nonce = pulse.integrity_metadata.get("nonce")
        if not nonce:
            raise ReplayAttackError("Missing unique nonce in request integrity metadata")

        self.replay_guard.validate_and_record(nonce, pulse.created_at_utc)
        context.state["replay_verified"] = True
        return context
