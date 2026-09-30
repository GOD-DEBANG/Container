"""
models/chunk_model.py
Dataclass representing a single chunk within a dataset.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class ChunkStatus(Enum):
    PENDING = auto()
    ALLOCATED = auto()
    PROCESSING = auto()
    PROCESSED = auto()
    FAILED = auto()


@dataclass
class ChunkModel:
    """
    Descriptor for one chunk of a dataset.

    chunk_id   — globally unique identifier (UUID string)
    dataset_id — parent dataset
    chunk_index — 0-based position in the dataset
    byte_offset — starting byte offset within the reconstructed dataset
    byte_length — number of bytes in this chunk
    checksum_sha256 — SHA-256 hex digest of raw chunk bytes
    status      — lifecycle status
    """

    chunk_id: str
    dataset_id: str
    chunk_index: int
    byte_offset: int
    byte_length: int
    checksum_sha256: str = ""
    status: ChunkStatus = ChunkStatus.PENDING

    def __post_init__(self) -> None:
        if self.chunk_index < 0:
            raise ValueError(f"chunk_index must be >= 0, got {self.chunk_index}")
        if self.byte_length <= 0:
            raise ValueError(f"byte_length must be > 0, got {self.byte_length}")
        if self.byte_offset < 0:
            raise ValueError(f"byte_offset must be >= 0, got {self.byte_offset}")
