"""
src/pulse/security/tokens.py

Compact, secure, short-lived token management with HMAC-SHA256 integrity.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from typing import Any, Dict

from ..core.errors import AuthenticationError


class TokenManager:
    def __init__(self, secret_key: bytes, default_ttl_seconds: int = 3600) -> None:
        if len(secret_key) < 32:
            raise ValueError("TokenManager secret_key must be at least 32 bytes")
        self.secret_key = secret_key
        self.default_ttl = default_ttl_seconds

    def issue_token(self, subject: str, claims: Dict[str, Any] | None = None, ttl_seconds: int | None = None) -> str:
        now = time.time()
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        payload = {
            "sub": subject,
            "iat": int(now),
            "nbf": int(now),
            "exp": int(now + ttl),
            "jti": uuid.uuid4().hex,
            "claims": claims or {},
        }
        encoded_payload = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("ascii").rstrip("=")
        sig = hmac.new(self.secret_key, encoded_payload.encode("ascii"), hashlib.sha256).digest()
        encoded_sig = base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")
        return f"{encoded_payload}.{encoded_sig}"

    def verify_token(self, token: str) -> Dict[str, Any]:
        parts = token.split(".")
        if len(parts) != 2:
            raise AuthenticationError("Malformed token structure")

        payload_b64, sig_b64 = parts
        # Pad back base64
        padded_sig = sig_b64 + "=" * (-len(sig_b64) % 4)
        try:
            expected_sig = base64.urlsafe_b64decode(padded_sig)
        except Exception:
            raise AuthenticationError("Invalid token signature encoding")

        actual_sig = hmac.new(self.secret_key, payload_b64.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise AuthenticationError("Invalid token signature")

        padded_payload = payload_b64 + "=" * (-len(payload_b64) % 4)
        try:
            payload = json.loads(base64.urlsafe_b64decode(padded_payload).decode("utf-8"))
        except Exception:
            raise AuthenticationError("Invalid token payload encoding")

        now = time.time()
        if payload.get("exp", 0) < now:
            raise AuthenticationError("Token has expired")
        if payload.get("nbf", 0) > now:
            raise AuthenticationError("Token is not yet valid (nbf)")

        return payload
