"""
resource_engine/resource_monitor.py

Collects ResourceSnapshots by coordinating CPUUnit, RAMUnit, and StorageUnit.
Caches benchmark results to avoid running intrusive benchmarks during processing.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Optional

from resource_engine.cpu_unit import CPUUnit, CPUMeasurement
from resource_engine.ram_unit import RAMUnit, RAMMeasurement
from resource_engine.storage_unit import StorageUnit, StorageMeasurement
from resource_engine.resource_snapshot import ResourceSnapshot


class ResourceMonitor:
    """
    Facade for collecting resource snapshots.

    Benchmark results (storage, RAM bandwidth) are cached and re-used
    during processing to avoid disrupting the measured workload.
    Callers can force a fresh benchmark by calling warm_up() again.
    """

    _STORAGE_BENCHMARK_CACHE_TTL_S: float = 300.0  # re-run every 5 min

    def __init__(self, storage_path: Optional[Path] = None) -> None:
        self._cpu_unit = CPUUnit()
        self._ram_unit = RAMUnit()
        self._storage_unit = StorageUnit(storage_path)

        self._cached_storage: Optional[StorageMeasurement] = None
        self._storage_cached_at: float = 0.0
        self._cached_ram_bandwidth: Optional[float] = None

    def warm_up(self) -> None:
        """
        Run initial benchmarks and warm up psutil cpu_percent baseline.
        Call once before starting the container.
        """
        self._cpu_unit.warm_up()
        self._cached_ram_bandwidth = self._ram_unit.benchmark_bandwidth_empirical(
            size_bytes=16 * 1024 * 1024  # 16 MiB
        )
        self._cached_storage = self._storage_unit.measure(
            benchmark_size_bytes=2 * 1024 * 1024  # 2 MiB
        )
        self._storage_cached_at = time.monotonic()

    def snapshot(
        self,
        active_workers: int = 0,
        queue_depth: int = 0,
    ) -> ResourceSnapshot:
        """
        Collect a current resource snapshot.
        Uses cached storage benchmark unless TTL has expired.
        """
        cpu = self._cpu_unit.measure()
        ram = self._ram_unit.measure()
        storage = self._get_storage_measurement()

        return ResourceSnapshot(
            snapshot_id=str(uuid.uuid4()),
            collected_at_ns=time.perf_counter_ns(),
            cpu=cpu,
            ram=ram,
            storage=storage,
            active_workers=active_workers,
            queue_depth=queue_depth,
        )

    @property
    def cached_ram_bandwidth(self) -> Optional[float]:
        return self._cached_ram_bandwidth

    def _get_storage_measurement(self) -> StorageMeasurement:
        now = time.monotonic()
        if (
            self._cached_storage is None
            or (now - self._storage_cached_at) > self._STORAGE_BENCHMARK_CACHE_TTL_S
        ):
            self._cached_storage = self._storage_unit.measure(
                benchmark_size_bytes=2 * 1024 * 1024
            )
            self._storage_cached_at = now
        return self._cached_storage
