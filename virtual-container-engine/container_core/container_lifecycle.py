"""
container_core/container_lifecycle.py

Manages state transitions for a VirtualContainer.
Enforces valid transitions according to ContainerState.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable

from models.container_model import ContainerState, assert_valid_transition

logger = logging.getLogger(__name__)


class ContainerLifecycle:
    """Thread-safe state machine for the container."""

    def __init__(self, initial_state: ContainerState = ContainerState.CREATED) -> None:
        self._state = initial_state
        self._lock = threading.Lock()
        self._listeners: list[Callable[[ContainerState, ContainerState], None]] = []

    @property
    def state(self) -> ContainerState:
        with self._lock:
            return self._state

    def transition(self, new_state: ContainerState) -> None:
        """
        Transition to new_state.
        Raises ValueError if transition is invalid.
        """
        with self._lock:
            assert_valid_transition(self._state, new_state)
            old_state = self._state
            self._state = new_state
            logger.debug("State transition: %s -> %s", old_state.name, new_state.name)
            
            for listener in self._listeners:
                try:
                    listener(old_state, new_state)
                except Exception as e:
                    logger.error("Error in state listener: %s", e)

    def add_listener(self, listener: Callable[[ContainerState, ContainerState], None]) -> None:
        with self._lock:
            self._listeners.append(listener)
