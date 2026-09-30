"""
layer2_processing/processing_layer.py

Orchestrates Layer 2: actual processing of allocated subchunks.
"""

from __future__ import annotations

import logging

from models.allocation_model import AllocationManifest
from models.processing_model import ProcessingResult, ProcessingStatus
from models.execution_metrics import ExecutionMetrics
from layer2_processing.processor import Processor
from layer2_processing.worker_manager import WorkerManager
from layer2_processing.execution_manager import ExecutionManager
from resource_engine.resource_monitor import ResourceMonitor
from resource_engine.resource_budget import ResourceBudget
from storage.storage_interface import StorageInterface

logger = logging.getLogger(__name__)


class ProcessingLayer:
    """
    Orchestrates the Layer 2 processing pipeline.
    """

    def __init__(
        self,
        processor: Processor,
        storage: StorageInterface,
        resource_monitor: ResourceMonitor,
    ) -> None:
        self._processor = processor
        self._storage = storage
        self._monitor = resource_monitor
        self._worker_mgr: WorkerManager | None = None

    def run(
        self,
        manifest: AllocationManifest,
        metrics: ExecutionMetrics,
        budget: ResourceBudget,
        desired_speed_bps: float = 0.0,
    ) -> list[ProcessingResult]:
        """
        Run the processing layer.
        """
        logger.info("Layer 2: processing %d subchunks", manifest.subchunk_count)

        self._worker_mgr = WorkerManager(
            processor=self._processor,
            storage=self._storage,
            max_workers=budget.effective_workers(1), # Real cores resolved in execution manager
        )

        exec_mgr = ExecutionManager(
            worker_manager=self._worker_mgr,
            resource_monitor=self._monitor,
            budget=budget,
            desired_speed_bps=desired_speed_bps,
        )

        results = exec_mgr.run(manifest, metrics)

        success_count = sum(1 for r in results if r.status == ProcessingStatus.SUCCESS)
        logger.info(
            "Layer 2: completed %d/%d subchunks successfully",
            success_count,
            manifest.subchunk_count,
        )

        return results

    def cancel(self) -> None:
        if self._worker_mgr:
            self._worker_mgr.cancel()
