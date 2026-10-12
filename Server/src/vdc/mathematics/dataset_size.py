"""
src/vdc/mathematics/dataset_size.py

Pure computational functions for dataset size estimation and actual size accounting.
No external dependencies, network, or filesystem calls.
"""

from __future__ import annotations

import math
from typing import Sequence


def estimate_dataset_size(record_count: int, average_record_bytes: float) -> int:
    """
    Estimate dataset size based on expected record count and mean record length:
        S_estimated = N * average_record_bytes

    Args:
        record_count: Number of records expected (N > 0).
        average_record_bytes: Mean size of a serialized record in bytes (> 0).

    Returns:
        Estimated total bytes rounded to nearest integer.

    Raises:
        ValueError: If record_count <= 0, average_record_bytes <= 0, or inputs are NaN/Inf.
    """
    if not isinstance(record_count, int):
        raise ValueError(f"record_count must be an integer, got {type(record_count).__name__}")
    if record_count <= 0:
        raise ValueError(f"record_count must be strictly positive, got {record_count}")

    if not isinstance(average_record_bytes, (int, float)):
        raise ValueError("average_record_bytes must be numeric")
    if math.isnan(average_record_bytes) or math.isinf(average_record_bytes):
        raise ValueError("average_record_bytes cannot be NaN or Infinite")
    if average_record_bytes <= 0.0:
        raise ValueError(f"average_record_bytes must be strictly positive, got {average_record_bytes}")

    estimated = record_count * average_record_bytes
    return int(math.floor(estimated + 0.5))


def calculate_actual_size(records: Sequence[bytes | bytearray | memoryview]) -> int:
    """
    Compute actual total size in bytes for a sequence of serialized records:
        S_actual = sum(len(r_i))

    Args:
        records: Sequence of raw serialized record buffers.

    Returns:
        Total byte length.

    Raises:
        ValueError: If records sequence is empty or contains non-buffer elements.
    """
    if not records:
        return 0

    total = 0
    for idx, r in enumerate(records):
        if not isinstance(r, (bytes, bytearray, memoryview)):
            raise ValueError(f"Record at index {idx} is not a valid buffer type: {type(r).__name__}")
        total += len(r)
    return total
