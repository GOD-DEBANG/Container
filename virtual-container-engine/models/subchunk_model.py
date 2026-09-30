"""
models/subchunk_model.py
Dataclass representing a single subchunk within a chunk.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class SubchunkStatus(Enum):
    PENDING = auto()
    ALLOCATED = auto()
    PROCESSING = auto()
    PROCESSED = auto()
    FAILED = auto()


@dataclass
class SubchunkModel:
    """
    Descriptor for one subchunk, which is a subdivision of a chunk.

    subchunk_id     — globally unique identifier
    chunk_id        — parent chunk
    dataset_id      — grandparent dataset
    subchunk_index  — 0-based position within the parent chunk
    byte_offset     — starting byte offset within the reconstructed dataset
    byte_length     — number of bytes in this subchunk
    checksum_sha256 — SHA-256 hex digest of raw subchunk bytes
    status          — lifecycle status
    """

    subchunk_id: str
    chunk_id: str
    dataset_id: str
    subchunk_index: int
    byte_offset: int
    byte_length: int
    checksum_sha256: str = ""
    status: SubchunkStatus = SubchunkStatus.PENDING

    def __post_init__(self) -> None:
        if self.subchunk_index < 0:
            raise ValueError(f"subchunk_index must be >= 0, got {self.subchunk_index}")
        if self.byte_length <= 0:
            raise ValueError(f"byte_length must be > 0, got {self.byte_length}")
        if self.byte_offset < 0:
            raise ValueError(f"byte_offset must be >= 0, got {self.byte_offset}")
