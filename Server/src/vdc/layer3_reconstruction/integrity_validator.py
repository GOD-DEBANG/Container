"""
src/vdc/layer3_reconstruction/integrity_validator.py

Validates dataset reconstruction integrity against expected specifications
and mathematical completion criteria.
"""

from __future__ import annotations

from typing import List

from ..models.allocation_model import AllocationManifest
from ..models.dataset_model import DatasetSpec
from ..mathematics.completion_formula import validate_completion, CompletionReport


class IntegrityValidator:
    @staticmethod
    def validate(
        spec: DatasetSpec,
        manifest: AllocationManifest,
        actual_bytes: int,
        actual_records: int,
        processed_chunk_ids: List[str],
        output_verified: bool,
    ) -> CompletionReport:
        expected_chunk_ids = {c.chunk_id for c in manifest.chunks}

        return validate_completion(
            expected_records=spec.estimated_records,
            actual_records=actual_records,
            expected_bytes=spec.target_size_bytes,
            actual_bytes=actual_bytes,
            expected_chunk_ids=expected_chunk_ids,
            actual_chunk_ids=processed_chunk_ids,
            output_verified=output_verified,
        )
