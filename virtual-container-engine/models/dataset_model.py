"""
models/dataset_model.py
Dataclass representing a complete dataset and its status.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path


class DatasetStatus(Enum):
    PENDING = auto()
    ALLOCATED = auto()
    PROCESSING = auto()
    RECONSTRUCTED = auto()
    VALIDATED = auto()
    COMMITTED = auto()
    FAILED = auto()


@dataclass
class DatasetModel:
    """
    Immutable descriptor of a dataset produced by the Virtual Container engine.

    The object holds metadata only; actual bytes reside on the filesystem.
    """

    dataset_id: str
    container_id: str
    target_size_bytes: int
    chunk_size_bytes: int
    subchunk_size_bytes: int
    seed: int
    status: DatasetStatus = DatasetStatus.PENDING
    allocated_bytes: int = 0
    chunk_count: int = 0
    subchunk_count: int = 0
    checksum_sha256: str = ""
    output_path: Path | None = None
    error_message: str = ""

    def __post_init__(self) -> None:
        if self.target_size_bytes <= 0:
            raise ValueError(f"target_size_bytes must be > 0, got {self.target_size_bytes}")
        if self.chunk_size_bytes <= 0 or self.chunk_size_bytes > self.target_size_bytes:
            raise ValueError(
                f"chunk_size_bytes must be in (0, target_size_bytes], "
                f"got {self.chunk_size_bytes}"
            )
        if self.subchunk_size_bytes <= 0 or self.subchunk_size_bytes > self.chunk_size_bytes:
            raise ValueError(
                f"subchunk_size_bytes must be in (0, chunk_size_bytes], "
                f"got {self.subchunk_size_bytes}"
            )
