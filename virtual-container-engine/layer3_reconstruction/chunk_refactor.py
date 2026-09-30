"""
layer3_reconstruction/chunk_refactor.py

Refactors processed subchunks back into their parent chunks.
"""

from __future__ import annotations

from models.allocation_model import AllocationManifest
from models.chunk_model import ChunkModel
from storage.storage_interface import StorageInterface


class ChunkRefactor:
    """Combines processed subchunks into full chunks."""

    def __init__(self, storage: StorageInterface) -> None:
        self._storage = storage

    def refactor(self, manifest: AllocationManifest, chunk: ChunkModel) -> str:
        """
        Merge processed subchunks for the given chunk into a single chunk file.
        Returns the relative path to the refactored chunk.
        """
        subs = manifest.subchunks.get(chunk.chunk_id, [])
        # Must refactor in index order
        subs_sorted = sorted(subs, key=lambda s: s.subchunk_index)

        chunk_path = f"chunks/{chunk.chunk_index}/chunk_{chunk.chunk_index}.bin"
        
        # In a real streaming implementation, we would append.
        # For simplicity in this demo, we'll read all subchunks into a buffer.
        buffer = bytearray()
        for sub in subs_sorted:
            sub_path = f"chunks/{chunk.chunk_index}/subchunks/{sub.subchunk_index}.proc.bin"
            data = self._storage.read(sub_path)
            if len(data) != sub.byte_length:
                raise ValueError(
                    f"Subchunk {sub.subchunk_index} size mismatch in storage: "
                    f"got {len(data)}, expected {sub.byte_length}"
                )
            buffer.extend(data)

        if len(buffer) != chunk.byte_length:
            raise ValueError(
                f"Refactored chunk {chunk.chunk_index} size mismatch: "
                f"got {len(buffer)}, expected {chunk.byte_length}"
            )

        self._storage.write(chunk_path, bytes(buffer))
        return chunk_path
