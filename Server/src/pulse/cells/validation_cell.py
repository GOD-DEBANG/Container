"""
src/pulse/cells/validation_cell.py

Request Validation Cell.
Validates dataset job payload parameters against schema constraints.
"""

from __future__ import annotations

from ..core.pipeline import BaseCell, PulseContext
from ..core.pulse import Pulse
from ..core.errors import ValidationError


class RequestValidationCell(BaseCell):
    name = "RequestValidationCell"
    input_contract = Pulse
    output_contract = Pulse

    async def process(self, context: PulseContext) -> PulseContext:
        payload = context.current_pulse.payload

        if "target_size_bytes" not in payload:
            raise ValidationError("Missing required field 'target_size_bytes'")

        target_size = payload.get("target_size_bytes")
        if not isinstance(target_size, int) or target_size <= 0:
            raise ValidationError(f"'target_size_bytes' must be a strictly positive integer, got {target_size}")

        chunk_size = payload.get("chunk_size_bytes", 1048576)
        if not isinstance(chunk_size, int) or chunk_size <= 0:
            raise ValidationError(f"'chunk_size_bytes' must be a positive integer, got {chunk_size}")

        subchunk_size = payload.get("subchunk_size_bytes", 262144)
        if not isinstance(subchunk_size, int) or subchunk_size <= 0:
            raise ValidationError(f"'subchunk_size_bytes' must be a positive integer, got {subchunk_size}")

        if subchunk_size > chunk_size:
            raise ValidationError(f"subchunk_size_bytes ({subchunk_size}) cannot exceed chunk_size_bytes ({chunk_size})")

        policy_str = payload.get("policy", "BALANCED").upper()
        if policy_str not in ("LOW_CPU", "BALANCED", "PERFORMANCE"):
            raise ValidationError(f"Invalid policy '{policy_str}'. Supported: LOW_CPU, BALANCED, PERFORMANCE")

        backend_str = payload.get("backend", "INLINE").upper()
        if backend_str not in ("INLINE", "DURABLE_WORKER", "LOCAL"):
            raise ValidationError(f"Invalid backend '{backend_str}'. Supported: INLINE, DURABLE_WORKER, LOCAL")

        context.state["validated_params"] = {
            "target_size_bytes": target_size,
            "chunk_size_bytes": chunk_size,
            "subchunk_size_bytes": subchunk_size,
            "seed": payload.get("seed", 42),
            "policy": policy_str,
            "backend": backend_str,
        }
        return context
