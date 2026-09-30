"""
services/dataset_generation_service.py

High-level service API for generating datasets.
This is the main entry point for programmatic integration.
"""

from __future__ import annotations

import logging
from pathlib import Path

from models.execution_metrics import ExecutionReport
from container_core.container_factory import ContainerFactory
from resource_engine.resource_budget import ResourceBudget, ExecutionPolicy

logger = logging.getLogger(__name__)


class DatasetGenerationService:
    """
    Service for generating deterministic datasets using the Virtual Container engine.
    """

    def __init__(self, data_dir: Path | None = None) -> None:
        base_dir = data_dir or (Path(__file__).parent.parent / "data")
        self._output_dir = base_dir / "output"
        self._manifest_dir = base_dir / "manifests"

    def generate(
        self,
        target_size_bytes: int,
        chunk_size_bytes: int,
        subchunk_size_bytes: int,
        seed: int = 42,
        policy: ExecutionPolicy = ExecutionPolicy.BALANCED,
        cpu_budget_cores: float = 0.0,
        worker_count: int = 0,
        ram_budget_bytes: int = 0,
    ) -> ExecutionReport:
        """
        Generate a dataset.

        Returns a structured ExecutionReport.
        Does NOT print to the console.
        """
        budget = ResourceBudget.from_policy(
            policy=policy,
            cpu_override=cpu_budget_cores,
            workers_override=worker_count,
            ram_override=ram_budget_bytes,
        )

        logger.info("Generating %d byte dataset", target_size_bytes)

        # Context manager guarantees container cleanup
        with ContainerFactory.create(
            target_size_bytes=target_size_bytes,
            chunk_size_bytes=chunk_size_bytes,
            subchunk_size_bytes=subchunk_size_bytes,
            seed=seed,
            budget=budget,
            persistent_storage_dir=self._output_dir,
            manifest_dir=self._manifest_dir,
        ) as container:
            
            report = container.run()
            
            return report
