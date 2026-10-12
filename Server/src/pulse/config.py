"""
src/pulse/config.py

PULSE Server environment configuration and platform settings.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PulseConfig:
    env: str
    host: str
    port: int
    debug: bool
    secret_key: bytes
    backend: str
    max_inline_dataset_bytes: int
    max_execution_duration_seconds: float
    storage_root: str
    redis_url: str | None

    @classmethod
    def load_from_env(cls) -> PulseConfig:
        env_mode = os.getenv("PULSE_ENV", "development").lower()
        secret_hex = os.getenv("PULSE_SECRET_KEY", "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")
        try:
            secret_key = bytes.fromhex(secret_hex)
        except Exception:
            secret_key = secret_hex.encode("utf-8")[:32].ljust(32, b"0")

        return cls(
            env=env_mode,
            host=os.getenv("PULSE_HOST", "0.0.0.0"),
            port=int(os.getenv("PULSE_PORT", "8000")),
            debug=os.getenv("PULSE_DEBUG", "false").lower() == "true",
            secret_key=secret_key,
            backend=os.getenv("VDC_EXECUTION_BACKEND", "INLINE").upper(),
            max_inline_dataset_bytes=int(os.getenv("VDC_INLINE_MAX_DATASET_BYTES", "268435456")),
            max_execution_duration_seconds=float(os.getenv("VDC_INLINE_MAX_DURATION_SECONDS", "120")),
            storage_root=os.getenv("VDC_STORAGE_ROOT", "data/storage"),
            redis_url=os.getenv("UPSTASH_REDIS_URL") or None,
        )


config = PulseConfig.load_from_env()
