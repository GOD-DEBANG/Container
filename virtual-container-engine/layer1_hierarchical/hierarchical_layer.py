"""
layer1_hierarchical/hierarchical_layer.py

Orchestrates Layer 1: dataset allocation.
Entry point called by the VirtualContainer.
"""

from __future__ import annotations

import logging

from models.allocation_model import AllocationManifest
from layer1_hierarchical.dataset_id_manager import DatasetIDManager
from layer1_hierarchical.allocation_manager import AllocationManager
from layer1_hierarchical.allocation_validator import AllocationValidator
from storage.storage_interface import StorageInterface
from storage.manifest_manager import ManifestManager

logger = logging.getLogger(__name__)


class HierarchicalLayer:
    """
    Layer 1 orchestrator: generate dataset_id → build chunks → build
    subchunks → generate bytes → validate manifest.
    """

    def __init__(
        self,
        storage: StorageInterface,
        manifest_manager: ManifestManager,
    ) -> None:
        self._storage = storage
        self._manifest_mgr = manifest_manager
        self._alloc_mgr = AllocationManager(storage)

    def run(
        self,
        container_id: str,
        target_size_bytes: int,
        chunk_size_bytes: int,
        subchunk_size_bytes: int,
        seed: int,
    ) -> AllocationManifest:
        """
        Run the full Layer 1 pipeline and return a validated manifest.
        Raises ValueError if validation fails.
        """
        logger.info("Layer 1: generating dataset_id for container %s", container_id)
        dataset_id = DatasetIDManager.generate(
            container_id=container_id,
            target_size_bytes=target_size_bytes,
            seed=seed,
        )
        logger.info("Layer 1: dataset_id=%s", dataset_id)

        logger.info(
            "Layer 1: allocating %d bytes (%d chunk_size, %d subchunk_size)",
            target_size_bytes,
            chunk_size_bytes,
            subchunk_size_bytes,
        )
        manifest = self._alloc_mgr.allocate(
            dataset_id=dataset_id,
            container_id=container_id,
            target_size_bytes=target_size_bytes,
            chunk_size_bytes=chunk_size_bytes,
            subchunk_size_bytes=subchunk_size_bytes,
            seed=seed,
        )

        logger.info(
            "Layer 1: allocated %d chunks, %d subchunks",
            manifest.chunk_count,
            manifest.subchunk_count,
        )

        result = AllocationValidator.validate(manifest)
        if not result.ok:
            raise ValueError(
                f"Allocation validation failed: {'; '.join(result.errors)}"
            )

        self._manifest_mgr.save(manifest)
        logger.info("Layer 1: manifest saved")
        return manifest
