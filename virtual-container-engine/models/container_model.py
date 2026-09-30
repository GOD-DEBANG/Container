"""
models/container_model.py
Enum of all valid container lifecycle states and their permitted transitions.
"""

from __future__ import annotations

from enum import Enum, auto


class ContainerState(Enum):
    CREATED = auto()
    INITIALIZED = auto()
    ALLOCATING = auto()
    PROCESSING = auto()
    RECONSTRUCTING = auto()
    VALIDATING = auto()
    COMMITTING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()
    DESTROYED = auto()


# Permitted transitions: from_state -> set of valid to_states
VALID_TRANSITIONS: dict[ContainerState, set[ContainerState]] = {
    ContainerState.CREATED: {ContainerState.INITIALIZED, ContainerState.CANCELLED},
    ContainerState.INITIALIZED: {ContainerState.ALLOCATING, ContainerState.CANCELLED},
    ContainerState.ALLOCATING: {ContainerState.PROCESSING, ContainerState.FAILED, ContainerState.CANCELLED},
    ContainerState.PROCESSING: {ContainerState.RECONSTRUCTING, ContainerState.FAILED, ContainerState.CANCELLED},
    ContainerState.RECONSTRUCTING: {ContainerState.VALIDATING, ContainerState.FAILED, ContainerState.CANCELLED},
    ContainerState.VALIDATING: {ContainerState.COMMITTING, ContainerState.FAILED, ContainerState.CANCELLED},
    ContainerState.COMMITTING: {ContainerState.COMPLETED, ContainerState.FAILED},
    ContainerState.COMPLETED: {ContainerState.DESTROYED},
    ContainerState.FAILED: {ContainerState.DESTROYED},
    ContainerState.CANCELLED: {ContainerState.DESTROYED},
    ContainerState.DESTROYED: set(),  # terminal
}


def is_valid_transition(from_state: ContainerState, to_state: ContainerState) -> bool:
    """Return True if the transition from_state → to_state is permitted."""
    return to_state in VALID_TRANSITIONS.get(from_state, set())


def assert_valid_transition(from_state: ContainerState, to_state: ContainerState) -> None:
    """Raise ValueError if the transition is not permitted."""
    if not is_valid_transition(from_state, to_state):
        raise ValueError(
            f"Invalid state transition: {from_state.name} → {to_state.name}. "
            f"Permitted: {[s.name for s in VALID_TRANSITIONS.get(from_state, set())]}"
        )
