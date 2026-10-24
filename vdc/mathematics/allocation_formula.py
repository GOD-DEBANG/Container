"""
src/vdc/mathematics/allocation_formula.py

Hierarchical and weighted dataset allocation formulas.
Implements integer-byte rounding using the largest remainder method
to guarantee exact conservation: sum(S_i) == S_total.
"""

from __future__ import annotations

import math
from typing import Sequence


def hierarchical_allocation(total_bytes: int, chunk_count: int) -> list[int]:
    """
    Equitably split total_bytes into chunk_count integer byte chunks:
        S_dataset = sum(S_chunk_i)

    Guarantees:
        - len(result) == chunk_count
        - all result elements >= 0
        - sum(result) == total_bytes

    Raises:
        ValueError: If total_bytes <= 0 or chunk_count <= 0.
    """
    if not isinstance(total_bytes, int) or total_bytes <= 0:
        raise ValueError(f"total_bytes must be positive integer, got {total_bytes}")
    if not isinstance(chunk_count, int) or chunk_count <= 0:
        raise ValueError(f"chunk_count must be positive integer, got {chunk_count}")

    base_size = total_bytes // chunk_count
    remainder = total_bytes % chunk_count

    # Distribute the remainder 1 byte at a time to the first remainder chunks
    allocations = [base_size + (1 if i < remainder else 0) for i in range(chunk_count)]
    assert sum(allocations) == total_bytes, "Allocation conservation violated"
    return allocations


def weighted_allocation(total_bytes: int, weights: Sequence[float]) -> list[int]:
    """
    Divide total_bytes across arbitrary weights:
        S_i = alpha_i * S_total
        sum(alpha_i) == 1.0

    Uses the Largest Remainder Method (Hamilton/Hare-Niemeyer Quota Method)
    to eliminate integer rounding errors while preserving total bytes exactly.

    Args:
        total_bytes: Total integer bytes to partition.
        weights: Sequence of positive relative weights summing to 1.0 (tolerance 1e-6).

    Returns:
        List of integer byte allocations such that sum(allocations) == total_bytes.

    Raises:
        ValueError: On negative bytes, empty weights, negative weight, NaN/Inf, or sum != 1.0.
    """
    if not isinstance(total_bytes, int) or total_bytes <= 0:
        raise ValueError(f"total_bytes must be a positive integer, got {total_bytes}")
    if not weights:
        raise ValueError("weights list cannot be empty")

    weight_sum = 0.0
    for idx, w in enumerate(weights):
        if not isinstance(w, (int, float)):
            raise ValueError(f"Weight at index {idx} must be numeric, got {type(w).__name__}")
        if math.isnan(w) or math.isinf(w):
            raise ValueError(f"Weight at index {idx} cannot be NaN or Infinite")
        if w < 0.0:
            raise ValueError(f"Weight at index {idx} cannot be negative: {w}")
        weight_sum += float(w)

    if abs(weight_sum - 1.0) > 1e-5:
        raise ValueError(f"Weights must sum to 1.0 (actual sum: {weight_sum:.7f})")

    exact_quotas = [w * total_bytes for w in weights]
    floored_allocations = [int(math.floor(q)) for q in exact_quotas]
    allocated_sum = sum(floored_allocations)
    remainder = total_bytes - allocated_sum

    # Fractional parts for ranking priority
    remainders = [(exact_quotas[i] - floored_allocations[i], i) for i in range(len(weights))]
    # Sort descending by fractional remainder
    remainders.sort(key=lambda x: x[0], reverse=True)

    result = list(floored_allocations)
    for i in range(remainder):
        target_idx = remainders[i][1]
        result[target_idx] += 1

    assert sum(result) == total_bytes, "Weighted allocation failed conservation test"
    assert all(x >= 0 for x in result), "Weighted allocation generated negative bytes"
    return result
