"""
container_core/execution_guard.py

Ensures operations only happen in valid states.
"""

from __future__ import annotations

from typing import Any, Callable, TypeVar
from functools import wraps

from models.container_model import ContainerState
from container_core.container_lifecycle import ContainerLifecycle

T = TypeVar("T")

class ExecutionGuard:
    """Decorator factory for ensuring methods only run in expected states."""

    @staticmethod
    def require_state(*allowed_states: ContainerState) -> Callable:
        """
        Decorator that raises RuntimeError if the container is not in
        one of the allowed states.
        Assumes the decorated method belongs to a class with a
        `_lifecycle` attribute of type ContainerLifecycle.
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
                current_state = self._lifecycle.state
                if current_state not in allowed_states:
                    raise RuntimeError(
                        f"Operation '{func.__name__}' not allowed in state "
                        f"{current_state.name}. Allowed states: "
                        f"{[s.name for s in allowed_states]}"
                    )
                return func(self, *args, **kwargs)
            return wrapper
        return decorator
