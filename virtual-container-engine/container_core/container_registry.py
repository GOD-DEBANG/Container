"""
container_core/container_registry.py

Global registry of active containers to ensure isolation and
limit concurrent executions.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from container_core.virtual_container import VirtualContainer

from resource_engine.resource_limits import ResourceLimits


class ContainerRegistry:
    """Thread-safe registry of active VirtualContainers."""
    
    _instance: ContainerRegistry | None = None
    _lock = threading.Lock()

    def __init__(self, limits: ResourceLimits | None = None) -> None:
        self._limits = limits or ResourceLimits()
        self._limits.validate()
        self._active: dict[str, VirtualContainer] = {}
        self._registry_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> ContainerRegistry:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def register(self, container: VirtualContainer) -> None:
        with self._registry_lock:
            if len(self._active) >= self._limits.max_concurrent_containers:
                raise RuntimeError(
                    f"Max concurrent containers ({self._limits.max_concurrent_containers}) reached"
                )
            if container.container_id in self._active:
                raise ValueError(f"Container {container.container_id} already registered")
            self._active[container.container_id] = container

    def unregister(self, container_id: str) -> None:
        with self._registry_lock:
            self._active.pop(container_id, None)

    @property
    def active_count(self) -> int:
        with self._registry_lock:
            return len(self._active)

    def clear(self) -> None:
        with self._registry_lock:
            self._active.clear()
