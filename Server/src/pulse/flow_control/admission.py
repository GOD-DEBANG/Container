"""
src/pulse/flow_control/admission.py

Server request admission controller.
Enforces Vercel platform boundaries: payload size <= 4.5 MB, dataset size limits,
and execution deadline constraints.
"""

from __future__ import annotations

from ..core.errors import ValidationError, ResourcePolicyError


class ServerAdmissionController:
    # Vercel request body limit is 4.5 MB
    MAX_REQUEST_PAYLOAD_BYTES = 4500000

    @classmethod
    def validate_request_body_size(cls, raw_body_bytes: int) -> None:
        if raw_body_bytes > cls.MAX_REQUEST_PAYLOAD_BYTES:
            raise ValidationError(
                f"Payload size ({raw_body_bytes} bytes) exceeds Vercel 4.5 MB limit "
                f"({cls.MAX_REQUEST_PAYLOAD_BYTES} bytes)"
            )

    @classmethod
    def validate_dataset_job_parameters(
        cls,
        target_size_bytes: int,
        backend: str,
        max_inline_bytes: int = 268435456, # 256 MB
    ) -> None:
        if target_size_bytes <= 0:
            raise ValidationError(f"target_size_bytes must be strictly positive, got {target_size_bytes}")

        if backend == "INLINE" and target_size_bytes > max_inline_bytes:
            raise ResourcePolicyError(
                f"Requested dataset size ({target_size_bytes} bytes) exceeds maximum "
                f"safe inline execution threshold ({max_inline_bytes} bytes). "
                f"Submit with backend=DURABLE_WORKER or reduce size."
            )
