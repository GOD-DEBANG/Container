"""
src/vdc/models/container_model.py

Virtual container lifecycle states and configuration models.
"""

from __future__ import annotations

from enum import Enum


class ContainerState(Enum):
    """
    State machine for the Virtual Container lifecycle:
    CREATED -> VALIDATING -> ALLOCATING -> PROCESSING -> RECONSTRUCTING ->
    VERIFYING -> PERSISTING -> COMPLETED -> DESTROYED
    """
    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    ALLOCATING = "ALLOCATING"
    PROCESSING = "PROCESSING"
    RECONSTRUCTING = "RECONSTRUCTING"
    VERIFYING = "VERIFYING"
    PERSISTING = "PERSISTING"
    COMPLETED = "COMPLETED"
    DESTROYED = "DESTROYED"

    # Exceptional states
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    RESOURCE_BLOCKED = "RESOURCE_BLOCKED"
