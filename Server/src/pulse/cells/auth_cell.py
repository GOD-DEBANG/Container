"""
src/pulse/cells/auth_cell.py

Authentication Cell.
Validates Bearer token credentials and attaches the authenticated principal to the Pulse.
"""

from __future__ import annotations

from ..core.pipeline import BaseCell, PulseContext
from ..core.pulse import Pulse
from ..core.errors import AuthenticationError
from ..security.tokens import TokenManager


class AuthCell(BaseCell):
    name = "AuthCell"
    input_contract = Pulse
    output_contract = Pulse

    def __init__(self, token_manager: TokenManager) -> None:
        self.token_manager = token_manager

    async def process(self, context: PulseContext) -> PulseContext:
        pulse = context.current_pulse
        auth_header = pulse.integrity_metadata.get("authorization", "")

        if not auth_header:
            raise AuthenticationError("Missing Authorization header")

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise AuthenticationError("Invalid Authorization header format; must be 'Bearer <token>'")

        token = parts[1]
        token_payload = self.token_manager.verify_token(token)
        principal_id = token_payload.get("sub", "unknown_principal")

        # Derive authenticated pulse
        context.current_pulse = pulse.with_principal(principal_id)
        context.state["principal_id"] = principal_id
        context.state["token_claims"] = token_payload.get("claims", {})
        return context
