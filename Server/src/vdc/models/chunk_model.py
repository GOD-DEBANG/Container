"""
src/vdc/models/chunk_model.py

Chunk descriptor data model.
Chunks represent primary hierarchical subdivisions of a dataset.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ChunkStatus(str, Enum):
    ALLOCATED = "ALLOCATED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    VERIFIED = "VERIFIED"
    COMMITTED = "COMMITTED"
    FAILED = "FAILED"


@dataclass
class ChunkModel:
    chunk_id: str
    dataset_id: str
    chunk_index: int
    byte_offset: int
    byte_length: int
    status: ChunkStatus = ChunkStatus.ALLOCATED
    checksum: str = ""
    record_count: int = 0
