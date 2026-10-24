"""
src/vdc/mathematics/completion_formula.py

Rigorous completion and integrity validation criteria.
Evaluates the 5 mandatory completion properties:
  1. Target record count reached.
  2. Actual byte totals validated.
  3. All expected chunks present.
  4. No unexpected duplicate chunks.
  5. Reconstruction and output persistence verified.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence, Set


@dataclass(frozen=True)
class CompletionReport:
    """Detailed completion evaluation summary."""
    is_complete: bool
    record_count_valid: bool
    byte_count_valid: bool
    all_chunks_present: bool
    no_duplicate_chunks: bool
    output_verified: bool
    missing_chunk_ids: list[str] = field(default_factory=list)
    duplicate_chunk_ids: list[str] = field(default_factory=list)
    failure_reasons: list[str] = field(default_factory=list)


def validate_completion(
    expected_records: int,
    actual_records: int,
    expected_bytes: int,
    actual_bytes: int,
    expected_chunk_ids: Set[str],
    actual_chunk_ids: Sequence[str],
    output_verified: bool,
) -> CompletionReport:
    """
    Pure validation function checking all termination criteria.

    Raises:
        ValueError: If negative counts or empty chunk sets are supplied.
    """
    if expected_records < 0 or actual_records < 0:
        raise ValueError("Record counts cannot be negative")
    if expected_bytes <= 0 or actual_bytes < 0:
        raise ValueError("Expected bytes must be > 0 and actual bytes >= 0")
    if not expected_chunk_ids:
        raise ValueError("expected_chunk_ids cannot be empty")

    failures: list[str] = []

    # 1. Record count
    rec_valid = (expected_records == actual_records)
    if not rec_valid:
        failures.append(f"Record count mismatch: expected {expected_records}, got {actual_records}")

    # 2. Byte count
    byte_valid = (expected_bytes == actual_bytes)
    if not byte_valid:
        failures.append(f"Byte count mismatch: expected {expected_bytes}, got {actual_bytes}")

    # 3 & 4. Chunk completeness and duplicate check
    actual_set = set(actual_chunk_ids)
    missing = sorted(list(expected_chunk_ids - actual_set))
    if missing:
        failures.append(f"Missing {len(missing)} chunks: {missing[:5]}...")

    seen: set[str] = set()
    duplicates: list[str] = []
    for cid in actual_chunk_ids:
        if cid in seen:
            duplicates.append(cid)
        seen.add(cid)

    if duplicates:
        failures.append(f"Detected {len(duplicates)} duplicate chunks in stream")

    all_present = (len(missing) == 0)
    no_dups = (len(duplicates) == 0)

    # 5. Output persistence verification
    if not output_verified:
        failures.append("Final persisted output failed verification checksum or integrity check")

    is_complete = rec_valid and byte_valid and all_present and no_dups and output_verified

    return CompletionReport(
        is_complete=is_complete,
        record_count_valid=rec_valid,
        byte_count_valid=byte_valid,
        all_chunks_present=all_present,
        no_duplicate_chunks=no_dups,
        output_verified=output_verified,
        missing_chunk_ids=missing,
        duplicate_chunk_ids=duplicates,
        failure_reasons=failures,
    )
