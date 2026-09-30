"""
services/container_service.py

Service for monitoring and managing active containers.
"""

from __future__ import annotations

from container_core.container_registry import ContainerRegistry
from container_core.virtual_container import VirtualContainer


class ContainerService:
    """Service to interact with the container registry."""
    
    def __init__(self) -> None:
        self._registry = ContainerRegistry.get_instance()

    def get_active_count(self) -> int:
        return self._registry.active_count

    def cancel_all(self) -> None:
        """Cancel all active containers."""
        # Using a list copy to avoid dictionary size change during iteration
        with self._registry._registry_lock:
            active_containers = list(self._registry._active.values())
            
        for container in active_containers:
            container.cancel()
