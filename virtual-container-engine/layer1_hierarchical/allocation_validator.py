"""
layer1_hierarchical/allocation_validator.py

Validates that an AllocationManifest satisfies all conservation and
structural constraints before Layer 2 processing begins.
"""

from __future__ import annotations

from dataclasses import dataclass

from models.allocation_model import AllocationManifest
from layer1_hierarchical.dataset_id_manager import DatasetIDManager


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str]

    def __bool__(self) -> bool:
        return self.ok


class AllocationValidator:
    """
    Validates an AllocationManifest before processing.

    Checks:
      1. dataset_id format is valid.
      2. All chunk dataset_ids match the manifest dataset_id.
      3. All subchunk dataset_ids and chunk_ids are consistent.
      4. chunk_index sequence is contiguous and 0-based.
      5. subchunk_index sequences per chunk are contiguous and 0-based.
      6. byte_offset continuity (no gaps, no overlaps).
      7. Byte conservation: chunk bytes sum to dataset total.
      8. Byte conservation: subchunk bytes sum to chunk totals.
    """

    @classmethod
    def validate(cls, manifest: AllocationManifest) -> ValidationResult:
        errors: list[str] = []

        # 1. Dataset ID format
        if not DatasetIDManager.validate(manifest.dataset_id):
            errors.append(f"Invalid dataset_id format: {manifest.dataset_id!r}")

        # 2–8: structural checks
        errors.extend(cls._check_chunks(manifest))
        errors.extend(cls._check_conservation(manifest))

        return ValidationResult(ok=len(errors) == 0, errors=errors)

    @staticmethod
    def _check_chunks(manifest: AllocationManifest) -> list[str]:
        errors: list[str] = []
        expected_offset = 0

        for i, chunk in enumerate(manifest.chunks):
            # chunk_index continuity
            if chunk.chunk_index != i:
                errors.append(
                    f"Chunk at position {i} has chunk_index {chunk.chunk_index} (expected {i})"
                )
            # dataset_id consistency
            if chunk.dataset_id != manifest.dataset_id:
                errors.append(
                    f"Chunk {chunk.chunk_id} dataset_id mismatch: "
                    f"{chunk.dataset_id} != {manifest.dataset_id}"
                )
            # byte_offset continuity
            if chunk.byte_offset != expected_offset:
                errors.append(
                    f"Chunk {i} byte_offset {chunk.byte_offset} != expected {expected_offset}"
                )
            expected_offset += chunk.byte_length

            # subchunk checks
            subs = manifest.subchunks.get(chunk.chunk_id, [])
            sub_offset = chunk.byte_offset
            for j, sub in enumerate(subs):
                if sub.subchunk_index != j:
                    errors.append(
                        f"Chunk {i} subchunk at position {j} has "
                        f"subchunk_index {sub.subchunk_index} (expected {j})"
                    )
                if sub.chunk_id != chunk.chunk_id:
                    errors.append(
                        f"Subchunk {sub.subchunk_id} chunk_id mismatch"
                    )
                if sub.dataset_id != manifest.dataset_id:
                    errors.append(
                        f"Subchunk {sub.subchunk_id} dataset_id mismatch"
                    )
                if sub.byte_offset != sub_offset:
                    errors.append(
                        f"Chunk {i} subchunk {j} byte_offset {sub.byte_offset} "
                        f"!= expected {sub_offset}"
                    )
                sub_offset += sub.byte_length

        return errors

    @staticmethod
    def _check_conservation(manifest: AllocationManifest) -> list[str]:
        ok, reason = manifest.validate_conservation()
        if not ok:
            return [f"Conservation violation: {reason}"]
        return []
