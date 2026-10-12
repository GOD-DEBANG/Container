"""
src/vdc/container_core/cleanup.py

Ensures complete cleanup of container-scoped temporary resources and buffers
upon normal completion, failure, cancellation, or unhandled exceptions.
Does NOT delete persisted datasets.
"""

from __future__ import annotations

import logging
from ..storage.temporary_storage import TemporaryStorage

logger = logging.getLogger(__name__)


class CleanupManager:
    def __init__(self, temp_storage: TemporaryStorage) -> None:
        self.temp_storage = temp_storage
        self.is_cleaned = False

    def perform_cleanup(self) -> bool:
        """
        Purge temporary storage directory and release transient resources.
        Returns True if cleanup succeeded without errors.
        """
        if self.is_cleaned:
            return True

        try:
            self.temp_storage.wipe_all()
            self.is_cleaned = True
            return True
        except Exception as exc:
            logger.error("Failed to perform temporary container cleanup: %s", exc)
            return False
