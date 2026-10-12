"""
src/vdc/container_core/lifecycle.py

State machine managing container lifecycle transitions.
"""

from __future__ import annotations

from typing import Set, Dict
from ..models.container_model import ContainerState


class LifecycleManager:
    # Valid deterministic transitions
    VALID_TRANSITIONS: Dict[ContainerState, Set[ContainerState]] = {
        ContainerState.CREATED: {ContainerState.VALIDATING, ContainerState.FAILED, ContainerState.CANCELLED},
        ContainerState.VALIDATING: {ContainerState.ALLOCATING, ContainerState.RESOURCE_BLOCKED, ContainerState.FAILED, ContainerState.CANCELLED},
        ContainerState.ALLOCATING: {ContainerState.PROCESSING, ContainerState.FAILED, ContainerState.CANCELLED},
        ContainerState.PROCESSING: {ContainerState.RECONSTRUCTING, ContainerState.FAILED, ContainerState.CANCELLED},
        ContainerState.RECONSTRUCTING: {ContainerState.VERIFYING, ContainerState.FAILED, ContainerState.CANCELLED},
        ContainerState.VERIFYING: {ContainerState.PERSISTING, ContainerState.FAILED, ContainerState.CANCELLED},
        ContainerState.PERSISTING: {ContainerState.COMPLETED, ContainerState.FAILED, ContainerState.CANCELLED},
        ContainerState.COMPLETED: {ContainerState.DESTROYED},
        ContainerState.RESOURCE_BLOCKED: {ContainerState.DESTROYED, ContainerState.FAILED},
        ContainerState.FAILED: {ContainerState.DESTROYED},
        ContainerState.CANCELLED: {ContainerState.DESTROYED},
        ContainerState.DESTROYED: set(),
    }

    def __init__(self, initial_state: ContainerState = ContainerState.CREATED) -> None:
        self._current_state = initial_state
        self._history: list[tuple[ContainerState, float]] = []

    @property
    def current_state(self) -> ContainerState:
        return self._current_state

    def transition_to(self, new_state: ContainerState) -> None:
        valid_next = self.VALID_TRANSITIONS.get(self._current_state, set())
        if new_state not in valid_next:
            raise ValueError(
                f"Illegal lifecycle transition: cannot move from {self._current_state.value} "
                f"to {new_state.value}"
            )
        self._current_state = new_state
