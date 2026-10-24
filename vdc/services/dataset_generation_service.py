"""
src/vdc/services/dataset_generation_service.py

High-level programmatic dataset generation service.
Independent of web frameworks, FastAPI, and presentation logic.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Callable

from ..models.dataset_model import DatasetSpec
from ..models.execution_metrics import ExecutionReport
from ..resource_engine.resource_budget import ExecutionPolicy, ResourceBudget
from ..container_core.factory import ContainerFactory


class DatasetGenerationService:
    def __init__(self, persistent_storage_dir: Optional[Path | str] = None) -> None:
        if persistent_storage_dir:
            self.persistent_storage_dir = Path(persistent_storage_dir)
        else:
            base = os.getenv("VDC_STORAGE_ROOT") or "data/storage"
            self.persistent_storage_dir = Path(base)

    def generate(
        self,
        job_id: str,
        target_size_bytes: int,
        chunk_size_bytes: int = 1048576,       # 1 MB default chunks
        subchunk_size_bytes: int = 262144,     # 256 KB default subchunks
        seed: int = 42,
        policy: ExecutionPolicy = ExecutionPolicy.BALANCED,
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        deadline_monotonic: Optional[float] = None,
    ) -> ExecutionReport:
        """
        Execute a dataset generation job inside a newly spawned Virtual Container.
        """
        budget = ResourceBudget.from_policy(policy)
        spec = DatasetSpec(
            target_size_bytes=target_size_bytes,
            chunk_size_bytes=chunk_size_bytes,
            subchunk_size_bytes=subchunk_size_bytes,
            seed=seed,
        )

        with ContainerFactory.create(
            job_id=job_id,
            spec=spec,
            budget=budget,
            persistent_storage_dir=self.persistent_storage_dir,
            progress_callback=progress_callback,
            deadline_monotonic=deadline_monotonic,
        ) as container:
            report = container.run()
            return report
