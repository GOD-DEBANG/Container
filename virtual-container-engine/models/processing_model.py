"""
models/processing_model.py
Result of processing a single subchunk.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class ProcessingStatus(Enum):
    SUCCESS = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class ProcessingResult:
    """
    Outcome of processing one subchunk.

    subchunk_id     — which subchunk was processed
    chunk_id        — parent chunk
    dataset_id      — grandparent dataset
    status          — success / failed / cancelled
    output_checksum — SHA-256 of the processed output bytes
    bytes_processed — number of bytes consumed by the processor
    elapsed_ns      — wall-clock duration in nanoseconds (perf_counter_ns)
    worker_id       — identifier of the worker that ran the task
    error           — error description if status != SUCCESS
    """

    subchunk_id: str
    chunk_id: str
    dataset_id: str
    status: ProcessingStatus
    output_checksum: str = ""
    bytes_processed: int = 0
    elapsed_ns: int = 0
    worker_id: str = ""
    error: str = ""

    @property
    def elapsed_seconds(self) -> float:
        return self.elapsed_ns / 1_000_000_000

    @property
    def throughput_bits_per_second(self) -> float:
        if self.elapsed_seconds <= 0:
            return 0.0
        return (self.bytes_processed * 8) / self.elapsed_seconds
