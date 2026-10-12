"""
src/vdc/container_core/factory.py

Factory creating unique, isolated VirtualContainer instances for every job.
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Optional, Callable

from ..models.dataset_model import DatasetSpec
from ..resource_engine.resource_budget import ResourceBudget
from ..storage.temporary_storage import TemporaryStorage
from ..storage.persistent_storage import PersistentStorage
from .virtual_container import VirtualContainer


class ContainerFactory:
    @staticmethod
    def create(
        job_id: str,
        spec: DatasetSpec,
        budget: ResourceBudget,
        persistent_storage_dir: Path | str,
        temp_base_dir: Optional[Path | str] = None,
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        deadline_monotonic: Optional[float] = None,
    ) -> VirtualContainer:
        """
        Create a new uniquely identified Virtual Container instance.
        """
        container_id = f"cnt_{uuid.uuid4().hex[:12]}"
        
        # Isolated temporary scratch directory for this container
        if temp_base_dir:
            temp_dir = Path(temp_base_dir) / container_id
        else:
            temp_dir = Path(tempfile.gettempdir()) / f"vdc_{container_id}"

        temp_storage = TemporaryStorage(temp_dir)
        persistent_storage = PersistentStorage(persistent_storage_dir)

        return VirtualContainer(
            container_id=container_id,
            job_id=job_id,
            spec=spec,
            budget=budget,
            temp_storage=temp_storage,
            persistent_storage=persistent_storage,
            progress_callback=progress_callback,
            deadline_monotonic=deadline_monotonic,
        )
