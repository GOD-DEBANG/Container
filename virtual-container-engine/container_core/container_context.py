"""
container_core/container_context.py

Context manager for VirtualContainer.
Guarantees cleanup on exit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generator

if TYPE_CHECKING:
    from container_core.virtual_container import VirtualContainer

class ContainerContext:
    """
    Context manager for VirtualContainer.
    """
    def __init__(self, container: VirtualContainer):
        self.container = container

    def __enter__(self) -> VirtualContainer:
        return self.container

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            # An exception occurred inside the with block
            self.container.cancel()
        
        # Always destroy
        self.container.destroy()
