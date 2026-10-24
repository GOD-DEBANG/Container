"""
src/vdc/models/dataset_model.py

Dataset specification and metadata models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass(frozen=True)
class DatasetSpec:
    """
    Validated dataset generation specification requested by a client.
    """
    target_size_bytes: int
    chunk_size_bytes: int
    subchunk_size_bytes: int
    seed: int = 42
    record_format: str = "binary"
    average_record_bytes: int = 256
    estimated_records: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DatasetMetadata:
    """
    Resulting metadata of a generated dataset artifact.
    """
    dataset_id: str
    target_size_bytes: int
    actual_size_bytes: int
    actual_records: int
    checksum_sha256: str
    chunk_count: int
    subchunk_count: int
    storage_path: str
    created_at_utc: float
