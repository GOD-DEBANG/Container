"""
container_core/container_factory.py

Factory for creating VirtualContainer instances.
Guarantees registry tracking and provides context manager support.
"""

from __future__ import annotations

from pathlib import Path

from container_core.virtual_container import VirtualContainer
from container_core.container_context import ContainerContext
from container_core.container_registry import ContainerRegistry
from resource_engine.resource_budget import ResourceBudget


class ContainerFactory:
    """Creates properly tracked VirtualContainer instances."""

    @staticmethod
    def create(
        target_size_bytes: int,
        chunk_size_bytes: int,
        subchunk_size_bytes: int,
        seed: int,
        budget: ResourceBudget,
        persistent_storage_dir: Path,
        manifest_dir: Path,
    ) -> ContainerContext:
        """
        Create a new VirtualContainer and wrap it in a ContainerContext.
        """
        container = VirtualContainer(
            target_size_bytes=target_size_bytes,
            chunk_size_bytes=chunk_size_bytes,
            subchunk_size_bytes=subchunk_size_bytes,
            seed=seed,
            budget=budget,
            persistent_storage_dir=persistent_storage_dir,
            manifest_dir=manifest_dir,
        )
        
        registry = ContainerRegistry.get_instance()
        registry.register(container)
        
        return ContainerContext(container)
