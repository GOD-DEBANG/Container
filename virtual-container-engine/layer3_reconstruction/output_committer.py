"""
layer3_reconstruction/output_committer.py

Atomically commits the validated dataset from temporary storage
to persistent storage.
"""

from __future__ import annotations

import logging
from pathlib import Path

from storage.storage_interface import StorageInterface
from storage.atomic_writer import AtomicWriter

logger = logging.getLogger(__name__)


class OutputCommitter:
    """Moves the rebuilt dataset to persistent storage atomically."""

    def __init__(self, temp_storage: StorageInterface, persistent_storage: StorageInterface) -> None:
        self._temp = temp_storage
        self._persist = persistent_storage

    def commit(self, dataset_id: str, temp_dataset_path: str) -> Path:
        """
        Read from temp storage and atomically write to persistent storage.
        Returns the absolute path to the committed dataset.
        """
        data = self._temp.read(temp_dataset_path)
        
        target_rel = f"{dataset_id}.bin"
        target_abs = self._persist.root() / target_rel

        logger.info("Committing dataset to %s", target_abs)
        AtomicWriter.write(target_abs, data)
        return target_abs
