"""
src/pulse/core/errors.py

Typed exception hierarchy for PULSE Server.
Standardizes error status codes and messages.
"""

from __future__ import annotations


class PulseError(Exception):
    status_code: int = 500
    error_code: str = "INTERNAL_SERVER_ERROR"

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AuthenticationError(PulseError):
    status_code = 401
    error_code = "AUTHENTICATION_FAILED"


class AuthorizationError(PulseError):
    status_code = 403
    error_code = "AUTHORIZATION_DENIED"


class SignatureVerificationError(PulseError):
    status_code = 401
    error_code = "INVALID_SIGNATURE"


class ReplayAttackError(PulseError):
    status_code = 409
    error_code = "REPLAY_DETECTED"


class ValidationError(PulseError):
    status_code = 400
    error_code = "VALIDATION_ERROR"


class ResourcePolicyError(PulseError):
    status_code = 422
    error_code = "POLICY_VIOLATION"


class BackpressureError(PulseError):
    status_code = 503
    error_code = "BACKPRESSURE_EXCEEDED"


class JobNotFoundError(PulseError):
    status_code = 404
    error_code = "JOB_NOT_FOUND"


class RouteNotFoundError(PulseError):
    status_code = 404
    error_code = "NOT_FOUND"


class MethodNotAllowedError(PulseError):
    status_code = 405
    error_code = "METHOD_NOT_ALLOWED"
