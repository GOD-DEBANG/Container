"""
src/pulse/observability/logger.py

Structured JSON logger with automatic redaction of sensitive credentials,
tokens, private keys, and raw confidential payloads.
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any


REDACTED_KEYS = {
    "authorization",
    "password",
    "token",
    "secret",
    "private_key",
    "dek",
    "kek",
    "signature",
    "api_key",
}


def redact_sensitive(obj: Any) -> Any:
    """Recursively scrub sensitive dictionary keys."""
    if isinstance(obj, dict):
        clean = {}
        for k, v in obj.items():
            if str(k).lower() in REDACTED_KEYS:
                clean[k] = "[REDACTED]"
            else:
                clean[k] = redact_sensitive(v)
        return clean
    elif isinstance(obj, list):
        return [redact_sensitive(item) for item in obj]
    return obj


class StructuredLogger:
    def __init__(self, service_name: str = "pulse-server") -> None:
        self.service_name = service_name

    def _log(self, level: str, message: str, **kwargs: Any) -> None:
        entry = {
            "timestamp_utc": time.time(),
            "service": self.service_name,
            "level": level,
            "message": message,
            "context": redact_sensitive(kwargs),
        }
        # Emit directly as a single-line JSON log entry
        sys.stdout.write(json.dumps(entry) + "\n")
        sys.stdout.flush()

    def info(self, message: str, **kwargs: Any) -> None:
        self._log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self._log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self._log("ERROR", message, **kwargs)


logger = StructuredLogger()
