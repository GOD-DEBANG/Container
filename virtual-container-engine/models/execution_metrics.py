"""
models/execution_metrics.py
Structured result objects returned by the core engine.

The core engine never prints these. Only output/output_console.py may
format and display them — and it is an optional, removable adapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ExecutionMetrics:
    """
    Per-container timing and throughput measurements.
    All timing values are measured using time.perf_counter_ns().
    """

    # Raw nanosecond timestamps
    start_ns: int = 0
    end_ns: int = 0

    # Processed data
    bytes_processed: int = 0
    chunk_count: int = 0
    subchunk_count: int = 0

    # CPU benchmark results
    cpu_benchmark_bytes: int = 0
    cpu_benchmark_elapsed_ns: int = 0
    cpu_benchmark_methodology: str = ""

    # Resource snapshots
    peak_ram_bytes: int = 0
    cpu_percent_avg: float = 0.0

    # Limiting resource (from actual speed controller)
    limiting_resource: str = "unknown"
    actual_speed_bits_per_second: float = 0.0
    desired_speed_bits_per_second: float = 0.0
    cpu_limit_bits_per_second: float = 0.0
    ram_limit_bits_per_second: float = 0.0
    io_limit_bits_per_second: float = 0.0

    @property
    def elapsed_ns(self) -> int:
        return max(0, self.end_ns - self.start_ns)

    @property
    def elapsed_seconds(self) -> float:
        return self.elapsed_ns / 1_000_000_000

    @property
    def throughput_bits_per_second(self) -> float:
        if self.elapsed_seconds <= 0:
            return 0.0
        return (self.bytes_processed * 8) / self.elapsed_seconds

    @property
    def cpu_benchmark_throughput_bits_per_second(self) -> float:
        """V_CPU_measured = 8*B / T  (Section 9 formula)"""
        t = self.cpu_benchmark_elapsed_ns / 1_000_000_000
        if t <= 0:
            return 0.0
        return (self.cpu_benchmark_bytes * 8) / t


@dataclass
class ExecutionReport:
    """
    Complete structured report returned by the core engine after a container run.

    This is the ONLY object that crosses the core→output boundary.
    The output adapter may read any field but must not mutate this object.
    """

    container_id: str
    dataset_id: str
    status: str                        # ContainerState.name
    target_size_bytes: int
    allocated_bytes: int
    processed_bytes: int
    remaining_bytes: int
    chunk_count: int
    subchunk_count: int
    metrics: ExecutionMetrics
    checksum_sha256: str
    integrity_verified: bool
    output_path: Optional[Path]
    cleanup_completed: bool
    error: str = ""

    # Resource report fields
    configured_cpu_budget_cores: float = 0.0
    detected_cpu_cores: int = 0
    process_cpu_percent: float = 0.0
    configured_ram_budget_bytes: int = 0
    process_ram_bytes: int = 0
    active_workers: int = 0
    resource_control_actions: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.status == "COMPLETED" and self.integrity_verified

    @property
    def elapsed_seconds(self) -> float:
        return self.metrics.elapsed_seconds

    @property
    def throughput_bits_per_second(self) -> float:
        return self.metrics.throughput_bits_per_second
