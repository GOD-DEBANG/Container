"""
src/pulse/core

Core abstractions: Pulse event model, pipeline, registry, router, and errors.
"""

from .pulse import Pulse
from .errors import (
    PulseError,
    AuthenticationError,
    AuthorizationError,
    SignatureVerificationError,
    ReplayAttackError,
    ValidationError,
    ResourcePolicyError,
    BackpressureError,
    JobNotFoundError,
    RouteNotFoundError,
    MethodNotAllowedError,
)
from .pipeline import BaseCell, PulseContext, Pipeline
from .registry import CellRegistry
from .router import CompiledRouter

__all__ = [
    "Pulse",
    "PulseError",
    "AuthenticationError",
    "AuthorizationError",
    "SignatureVerificationError",
    "ReplayAttackError",
    "ValidationError",
    "ResourcePolicyError",
    "BackpressureError",
    "JobNotFoundError",
    "RouteNotFoundError",
    "MethodNotAllowedError",
    "BaseCell",
    "PulseContext",
    "Pipeline",
    "CellRegistry",
    "CompiledRouter",
]
