"""
container_core/cleanup_manager.py

Coordinates the destruction and cleanup of container resources.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from storage.temporary_storage import TemporaryStorage
    from layer2_processing.processing_layer import ProcessingLayer

logger = logging.getLogger(__name__)


class CleanupManager:
    """Safely cleans up container resources."""

    @staticmethod
    def cleanup(
        container_id: str,
        temp_storage: TemporaryStorage | None,
        processing_layer: ProcessingLayer | None,
    ) -> bool:
        """
        Execute cleanup sequence.
        Returns True if successful.
        """
        success = True
        logger.info("Cleaning up container %s", container_id)

        # 1. Stop processing layer
        if processing_layer:
            try:
                processing_layer.cancel()
                logger.debug("Processing layer cancelled")
            except Exception as e:
                logger.error("Error cancelling processing layer: %s", e)
                success = False

        # 2. Destroy temporary storage
        if temp_storage:
            try:
                temp_storage.destroy()
                logger.debug("Temporary storage destroyed")
            except Exception as e:
                logger.error("Error destroying temporary storage: %s", e)
                success = False

        return success
