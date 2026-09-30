"""
resource_engine/resource_snapshot.py

Composite snapshot of all resource measurements at one point in time.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from resource_engine.cpu_unit import CPUMeasurement
from resource_engine.ram_unit import RAMMeasurement
from resource_engine.storage_unit import StorageMeasurement


@dataclass
class ResourceSnapshot:
    """
    Unified snapshot of CPU, RAM, and storage measurements.
    Produced by ResourceMonitor and consumed by ResourceNormalizer.
    """
    snapshot_id: str
    collected_at_ns: int
    cpu: CPUMeasurement
    ram: RAMMeasurement
    storage: StorageMeasurement

    # Derived: active workers observed at snapshot time
    active_workers: int = 0
    queue_depth: int = 0

    @property
    def age_seconds(self) -> float:
        return (time.perf_counter_ns() - self.collected_at_ns) / 1_000_000_000
