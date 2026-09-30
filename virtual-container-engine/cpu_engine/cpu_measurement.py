"""
cpu_engine/cpu_measurement.py

Provides a session-scoped CPU measurement context.
Collects CPU state before and after a workload execution window.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from resource_engine.cpu_unit import CPUUnit, CPUMeasurement


@dataclass
class CPUMeasurementSession:
    """
    Records CPU state at start and end of a processing session.
    """
    start_snapshot: Optional[CPUMeasurement] = None
    end_snapshot: Optional[CPUMeasurement] = None
    start_ns: int = 0
    end_ns: int = 0

    def begin(self, cpu_unit: CPUUnit) -> None:
        self.start_ns = time.perf_counter_ns()
        self.start_snapshot = cpu_unit.measure()

    def end(self, cpu_unit: CPUUnit) -> None:
        self.end_ns = time.perf_counter_ns()
        self.end_snapshot = cpu_unit.measure()

    @property
    def elapsed_ns(self) -> int:
        return max(0, self.end_ns - self.start_ns)

    @property
    def elapsed_seconds(self) -> float:
        return self.elapsed_ns / 1_000_000_000

    @property
    def process_cpu_percent_avg(self) -> Optional[float]:
        """Average process CPU% across start and end snapshots."""
        start_pct = (
            self.start_snapshot.process_cpu_percent
            if self.start_snapshot
            else None
        )
        end_pct = (
            self.end_snapshot.process_cpu_percent
            if self.end_snapshot
            else None
        )
        values = [v for v in (start_pct, end_pct) if v is not None]
        if not values:
            return None
        return sum(values) / len(values)
