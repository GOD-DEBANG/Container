"""
src/vdc/container_core

Virtual Container core lifecycle and execution components.
"""

from .lifecycle import LifecycleManager
from .cleanup import CleanupManager
from .virtual_container import VirtualContainer
from .factory import ContainerFactory

__all__ = [
    "LifecycleManager",
    "CleanupManager",
    "VirtualContainer",
    "ContainerFactory",
]
