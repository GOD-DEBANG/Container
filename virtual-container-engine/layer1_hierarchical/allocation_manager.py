"""
layer1_hierarchical/allocation_manager.py

Coordinates ChunkCreator and SubchunkCreator to produce a complete
AllocationManifest and generates the initial dataset byte stream
into the container's temporary storage.

Data generation is incremental (streaming by subchunk).
The full dataset is never held in a single byte array.
"""

from __future__ import annotations

import hashlib
import logging
import random
from pathlib import Path

from models.allocation_model import AllocationManifest
from models.chunk_model import ChunkStatus
from models.subchunk_model import SubchunkStatus
from layer1_hierarchical.chunk_creator import ChunkCreator
from layer1_hierarchical.subchunk_creator import SubchunkCreator
from storage.storage_interface import StorageInterface

logger = logging.getLogger(__name__)


class AllocationManager:
    """
    Builds the complete AllocationManifest and streams dataset bytes
    into temporary storage.

    Memory model: at most one subchunk worth of bytes is in RAM
    at any given time during allocation.
    """

    def __init__(self, storage: StorageInterface) -> None:
        self._storage = storage

    def allocate(
        self,
        dataset_id: str,
        container_id: str,
        target_size_bytes: int,
        chunk_size_bytes: int,
        subchunk_size_bytes: int,
        seed: int,
    ) -> AllocationManifest:
        """
        Build chunks, subchunks, generate bytes, and return the manifest.

        Bytes are written to temporary storage using the subchunk path
        convention: chunks/<chunk_index>/subchunks/<subchunk_index>.bin
        """
        rng = random.Random(seed)

        chunks = ChunkCreator.create_chunks(
            dataset_id=dataset_id,
            dataset_total_bytes=target_size_bytes,
            chunk_size_bytes=chunk_size_bytes,
        )

        subchunks_map: dict[str, list] = {}

        for chunk in chunks:
            subs = SubchunkCreator.create_subchunks(chunk, subchunk_size_bytes)
            subchunks_map[chunk.chunk_id] = subs

            chunk_hash = hashlib.sha256()
            for sub in subs:
                # Generate deterministic bytes for this subchunk
                data = bytes(rng.randint(0, 255) for _ in range(sub.byte_length))

                # Compute subchunk checksum
                sub.checksum_sha256 = hashlib.sha256(data).hexdigest()
                sub.status = SubchunkStatus.ALLOCATED

                # Write to temporary storage
                rel_path = (
                    f"chunks/{chunk.chunk_index}/"
                    f"subchunks/{sub.subchunk_index}.bin"
                )
                self._storage.write(rel_path, data)
                chunk_hash.update(data)

            chunk.checksum_sha256 = chunk_hash.hexdigest()
            chunk.status = ChunkStatus.ALLOCATED
            logger.debug(
                "Allocated chunk %d (%d bytes, %d subchunks)",
                chunk.chunk_index,
                chunk.byte_length,
                len(subs),
            )

        manifest = AllocationManifest(
            dataset_id=dataset_id,
            container_id=container_id,
            dataset_total_bytes=target_size_bytes,
            chunks=chunks,
            subchunks=subchunks_map,
        )
        return manifest
