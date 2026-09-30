"""
models/allocation_model.py
Complete allocation manifest produced by Layer 1 hierarchical allocation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from models.chunk_model import ChunkModel
from models.subchunk_model import SubchunkModel


@dataclass
class AllocationManifest:
    """
    Complete hierarchical allocation descriptor for a single dataset.

    Conservation invariant:
        dataset_total_bytes == sum(c.byte_length for c in chunks)
        chunk.byte_length   == sum(s.byte_length for s in subchunks[chunk])
    """

    dataset_id: str
    container_id: str
    dataset_total_bytes: int
    chunks: list[ChunkModel] = field(default_factory=list)
    # Map from chunk_id -> ordered list of subchunks
    subchunks: dict[str, list[SubchunkModel]] = field(default_factory=dict)
    manifest_path: Path | None = None

    # ------------------------------------------------------------------ #
    # Derived properties
    # ------------------------------------------------------------------ #

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)

    @property
    def subchunk_count(self) -> int:
        return sum(len(v) for v in self.subchunks.values())

    @property
    def all_subchunks(self) -> list[SubchunkModel]:
        """Flat ordered list of every subchunk across all chunks."""
        result: list[SubchunkModel] = []
        for chunk in self.chunks:
            result.extend(self.subchunks.get(chunk.chunk_id, []))
        return result

    # ------------------------------------------------------------------ #
    # Validation helpers
    # ------------------------------------------------------------------ #

    def validate_conservation(self) -> tuple[bool, str]:
        """
        Verify that allocation byte sizes are conserved at every level.

        Returns (ok, reason).
        """
        total = sum(c.byte_length for c in self.chunks)
        if total != self.dataset_total_bytes:
            return (
                False,
                f"Chunk bytes {total} != dataset_total_bytes {self.dataset_total_bytes}",
            )
        for chunk in self.chunks:
            sub_list = self.subchunks.get(chunk.chunk_id, [])
            sub_total = sum(s.byte_length for s in sub_list)
            if sub_total != chunk.byte_length:
                return (
                    False,
                    f"Subchunk bytes {sub_total} != chunk {chunk.chunk_id} "
                    f"byte_length {chunk.byte_length}",
                )
        return True, "ok"
