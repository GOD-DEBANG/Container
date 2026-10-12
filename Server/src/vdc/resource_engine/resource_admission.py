"""
src/vdc/resource_engine/resource_admission.py

Admission control validating system memory, disk, and configured execution limits
before initiating dataset generation.
"""

from __future__ import annotations

from typing import Tuple

from ..models.dataset_model import DatasetSpec
from .resource_monitor import ResourceMonitor
from .resource_budget import ResourceBudget


class ResourceAdmissionController:
    @staticmethod
    def check_admission(
        spec: DatasetSpec,
        budget: ResourceBudget,
        max_allowed_dataset_bytes: int = 268435456,  # 256 MB safe limit
    ) -> Tuple[bool, str]:
        """
        Validate whether the workload can be safely admitted.
        """
        if spec.target_size_bytes <= 0:
            return False, f"Invalid target_size_bytes: {spec.target_size_bytes}"

        if spec.target_size_bytes > max_allowed_dataset_bytes:
            return False, (
                f"Workload size ({spec.target_size_bytes} bytes) exceeds maximum "
                f"allowed execution limit ({max_allowed_dataset_bytes} bytes)"
            )

        snapshot = ResourceMonitor.take_snapshot()

        # Check memory reserve
        # Minimum required memory is the working chunk buffer + reserve
        working_memory_required = spec.chunk_size_bytes * budget.concurrency_limit + budget.memory_reserve_bytes
        if snapshot.ram_available_bytes < working_memory_required:
            return False, (
                f"Insufficient RAM: available {snapshot.ram_available_bytes} bytes, "
                f"required {working_memory_required} bytes (reserve: {budget.memory_reserve_bytes})"
            )

        # Check disk space (need at least 2x target size for temp chunks + reconstructed output)
        disk_required = spec.target_size_bytes * 2 + (10 * 1024 * 1024)
        if snapshot.disk_available_bytes < disk_required:
            return False, (
                f"Insufficient disk space: available {snapshot.disk_available_bytes} bytes, "
                f"required {disk_required} bytes"
            )

        return True, "Admission approved"
