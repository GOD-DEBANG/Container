"""
layer3_reconstruction/refactoring_layer.py

Orchestrates Layer 3: Validation, Chunk Refactoring, Dataset Rebuilding,
Integrity Validation, and Output Commit.
"""

from __future__ import annotations

import logging
from pathlib import Path

from models.allocation_model import AllocationManifest
from models.processing_model import ProcessingResult
from layer3_reconstruction.id_validator import IDValidator
from layer3_reconstruction.chunk_refactor import ChunkRefactor
from layer3_reconstruction.dataset_rebuilder import DatasetRebuilder
from layer3_reconstruction.integrity_validator import IntegrityValidator
from layer3_reconstruction.output_committer import OutputCommitter
from storage.storage_interface import StorageInterface

logger = logging.getLogger(__name__)


class RefactoringLayer:
    """Orchestrates the Layer 3 reconstruction pipeline."""

    def __init__(self, temp_storage: StorageInterface, persistent_storage: StorageInterface) -> None:
        self._temp = temp_storage
        self._persist = persistent_storage
        self._chunk_refactor = ChunkRefactor(temp_storage)
        self._rebuilder = DatasetRebuilder(temp_storage)
        self._validator = IntegrityValidator(temp_storage)
        self._committer = OutputCommitter(temp_storage, persistent_storage)

    def run(
        self,
        manifest: AllocationManifest,
        results: list[ProcessingResult],
    ) -> tuple[bool, str, Path | None]:
        """
        Run Layer 3 pipeline.
        Returns (integrity_verified, checksum, final_output_path).
        """
        logger.info("Layer 3: Validating %d results", len(results))
        IDValidator.validate_results(manifest, results)

        logger.info("Layer 3: Refactoring chunks")
        chunk_paths: dict[str, str] = {}
        for chunk in manifest.chunks:
            chunk_paths[chunk.chunk_id] = self._chunk_refactor.refactor(manifest, chunk)

        logger.info("Layer 3: Rebuilding dataset")
        temp_dataset_path = self._rebuilder.rebuild(manifest, chunk_paths)

        logger.info("Layer 3: Validating integrity")
        valid, checksum = self._validator.validate(manifest, temp_dataset_path)

        if not valid:
            raise ValueError("Integrity validation failed on rebuilt dataset")

        logger.info("Layer 3: Committing to persistent storage")
        output_path = self._committer.commit(manifest.dataset_id, temp_dataset_path)

        return valid, checksum, output_path
