"""
layer3_reconstruction/dataset_rebuilder.py

Rebuilds the full dataset from refactored chunks.
"""

from __future__ import annotations

from models.allocation_model import AllocationManifest
from storage.storage_interface import StorageInterface


class DatasetRebuilder:
    """Combines refactored chunks into the final dataset file."""

    def __init__(self, storage: StorageInterface) -> None:
        self._storage = storage

    def rebuild(self, manifest: AllocationManifest, chunk_paths: dict[str, str]) -> str:
        """
        Merge chunk files into the final dataset in temporary storage.
        Returns the relative path to the rebuilt dataset.
        """
        # Must rebuild in index order
        chunks_sorted = sorted(manifest.chunks, key=lambda c: c.chunk_index)

        dataset_path = f"dataset_{manifest.dataset_id}.bin"
        
        # In a real streaming implementation, we would append.
        # For simplicity in this demo, we'll read all chunks into a buffer.
        buffer = bytearray()
        for chunk in chunks_sorted:
            path = chunk_paths[chunk.chunk_id]
            data = self._storage.read(path)
            if len(data) != chunk.byte_length:
                raise ValueError(
                    f"Chunk {chunk.chunk_index} size mismatch in storage: "
                    f"got {len(data)}, expected {chunk.byte_length}"
                )
            buffer.extend(data)

        if len(buffer) != manifest.dataset_total_bytes:
            raise ValueError(
                f"Rebuilt dataset size mismatch: "
                f"got {len(buffer)}, expected {manifest.dataset_total_bytes}"
            )

        self._storage.write(dataset_path, bytes(buffer))
        return dataset_path
