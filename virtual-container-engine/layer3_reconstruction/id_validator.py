"""
layer3_reconstruction/id_validator.py

Validates IDs and sequences of processed results before reconstruction.
"""

from __future__ import annotations

from models.allocation_model import AllocationManifest
from models.processing_model import ProcessingResult


class IDValidator:
    """Validates processed results against the manifest."""

    @staticmethod
    def validate_results(
        manifest: AllocationManifest,
        results: list[ProcessingResult],
    ) -> None:
        """
        Verify all subchunks are present and have correct IDs.
        Raises ValueError if anything is missing or invalid.
        """
        expected_subs = {s.subchunk_id: s for s in manifest.all_subchunks}
        seen: set[str] = set()

        for result in results:
            if result.status.name != "SUCCESS":
                raise ValueError(
                    f"Subchunk {result.subchunk_id} did not succeed: {result.error}"
                )

            if result.subchunk_id not in expected_subs:
                raise ValueError(f"Unknown subchunk ID in results: {result.subchunk_id}")

            if result.subchunk_id in seen:
                raise ValueError(f"Duplicate subchunk result: {result.subchunk_id}")

            seen.add(result.subchunk_id)

            sub = expected_subs[result.subchunk_id]
            if result.chunk_id != sub.chunk_id:
                raise ValueError(
                    f"Subchunk {result.subchunk_id} chunk_id mismatch: "
                    f"got {result.chunk_id}, expected {sub.chunk_id}"
                )
            if result.dataset_id != sub.dataset_id:
                raise ValueError(
                    f"Subchunk {result.subchunk_id} dataset_id mismatch: "
                    f"got {result.dataset_id}, expected {sub.dataset_id}"
                )
            if result.bytes_processed != sub.byte_length:
                raise ValueError(
                    f"Subchunk {result.subchunk_id} length mismatch: "
                    f"got {result.bytes_processed}, expected {sub.byte_length}"
                )

        if len(seen) != len(expected_subs):
            missing = set(expected_subs.keys()) - seen
            raise ValueError(f"Missing results for {len(missing)} subchunks")
