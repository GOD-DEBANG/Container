"""
src/vdc/models/subchunk_model.py

Subchunk descriptor data model.
Subchunks are atomic work units allocated within a chunk.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SubchunkStatus(str, Enum):
    ALLOCATED = "ALLOCATED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class SubchunkModel:
    subchunk_id: str
    chunk_id: str
    dataset_id: str
    subchunk_index: int
    byte_offset: int
    byte_length: int
    status: SubchunkStatus = SubchunkStatus.ALLOCATED
    checksum: str = ""
    record_count: int = 0
