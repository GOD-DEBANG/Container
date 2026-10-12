"""
src/pulse/cells/signature_cell.py

Signature Verification Cell.
Verifies Ed25519 digital signatures on the incoming Pulse payload.
"""

from __future__ import annotations

import base64
import json
from cryptography.hazmat.primitives.asymmetric import ed25519

from ..core.pipeline import BaseCell, PulseContext
from ..core.pulse import Pulse
from ..core.errors import SignatureVerificationError
from ..security.crypto import CryptoEngine


class SignatureVerificationCell(BaseCell):
    name = "SignatureVerificationCell"
    input_contract = Pulse
    output_contract = Pulse

    async def process(self, context: PulseContext) -> PulseContext:
        pulse = context.current_pulse
        meta = pulse.integrity_metadata
        sig_b64 = meta.get("signature_b64")
        pub_b64 = meta.get("public_key_b64")

        if not sig_b64 or not pub_b64:
            raise SignatureVerificationError("Missing required digital signature or public key in integrity metadata")

        try:
            signature_bytes = base64.b64decode(sig_b64)
            pub_bytes = base64.b64decode(pub_b64)
            pub_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
        except Exception as exc:
            raise SignatureVerificationError(f"Malformed signature or public key: {str(exc)}")

        # Deterministic canonical serialization of payload for verification
        canonical_bytes = json.dumps(pulse.payload, sort_keys=True).encode("utf-8")
        CryptoEngine.verify_ed25519(pub_key, signature_bytes, canonical_bytes)

        context.state["signature_verified"] = True
        return context
