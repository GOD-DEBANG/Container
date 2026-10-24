"""
src/vdc/models/execution_metrics.py

Detailed metrics and typed execution reports.
Strictly separates configured limits, estimated rates, measured generation throughput,
and measured persistence throughput.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class ResourceSnapshot:
    """Instantaneous snapshot of hardware and runtime utilization."""
    timestamp: float
    cpu_percent: float
    ram_used_bytes: int
    ram_available_bytes: int
    disk_available_bytes: int
    hard_cpu_enforcement_available: bool = False


@dataclass
class ExecutionMetrics:
    """Detailed runtime metrics accumulated over container execution."""
    start_time_monotonic: float = 0.0
    end_time_monotonic: float = 0.0
    total_elapsed_seconds: float = 0.0

    # Separate throughput categories (never conflated)
    estimated_throughput_bytes_per_sec: float = 0.0
    configured_rate_limit_bytes_per_sec: Optional[float] = None
    measured_generation_throughput_bytes_per_sec: float = 0.0
    measured_persistence_throughput_bytes_per_sec: float = 0.0
    end_to_end_throughput_bytes_per_sec: float = 0.0

    # Volume accounting
    actual_generated_bytes: int = 0
    actual_persisted_bytes: int = 0
    actual_records_generated: int = 0

    # Performance breakdowns
    limiting_resource: str = "unconstrained"
    queue_wait_seconds: float = 0.0
    chunk_processing_seconds: float = 0.0
    reconstruction_seconds: float = 0.0
    verification_seconds: float = 0.0
    persistence_seconds: float = 0.0

    resource_snapshots: List[ResourceSnapshot] = field(default_factory=list)


@dataclass
class ExecutionReport:
    """Typed report returned upon container run completion."""
    container_id: str
    job_id: str
    dataset_id: str
    success: bool
    status: str
    metrics: ExecutionMetrics
    storage_path: Optional[str] = None
    checksum_sha256: Optional[str] = None
    chunks_processed: int = 0
    subchunks_processed: int = 0
    cleanup_successful: bool = False
    error: Optional[str] = None
    extra_metadata: Dict[str, Any] = field(default_factory=dict)
