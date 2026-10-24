"""
src/vdc/models/allocation_model.py

Allocation manifest model representing hierarchical partitioning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .chunk_model import ChunkModel
from .subchunk_model import SubchunkModel


@dataclass
class AllocationManifest:
    """
    Hierarchical allocation manifest describing the complete layout of a dataset.
    """
    dataset_id: str
    target_bytes: int
    chunks: List[ChunkModel] = field(default_factory=list)
    subchunks: List[SubchunkModel] = field(default_factory=list)

    @property
    def total_chunk_bytes(self) -> int:
        return sum(c.byte_length for c in self.chunks)

    @property
    def total_subchunk_bytes(self) -> int:
        return sum(s.byte_length for s in self.subchunks)

    def is_conserved(self) -> bool:
        return (
            self.total_chunk_bytes == self.target_bytes
            and self.total_subchunk_bytes == self.target_bytes
        )
