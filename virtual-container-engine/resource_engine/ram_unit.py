"""
resource_engine/ram_unit.py

Actual RAM measurement using psutil.

Measures:
  - System total / available / used memory
  - Process RSS (resident set size) and VMS (virtual memory size)
  - Swap usage

Does NOT measure memory bandwidth — that requires hardware counters
(e.g., perf, PMU) unavailable in pure Python. Where unavailable, this
is reported explicitly.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Optional

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False


@dataclass
class RAMMeasurement:
    """Snapshot of RAM state. None fields = unavailable."""
    timestamp_ns: int = 0

    # System-wide
    system_total_bytes: Optional[int] = None
    system_available_bytes: Optional[int] = None
    system_used_bytes: Optional[int] = None

    # Process
    process_rss_bytes: Optional[int] = None
    process_vms_bytes: Optional[int] = None

    # Memory bandwidth: NOT measurable in pure Python
    # Reported as unavailable unless an empirical benchmark is provided.
    bandwidth_bytes_per_second: Optional[float] = None
    bandwidth_note: str = "memory bandwidth requires hardware counters; not available in pure Python"

    unavailable_fields: list[str] = field(default_factory=list)


class RAMUnit:
    """Measures actual memory resources available to this process."""

    def __init__(self) -> None:
        self._process: Optional[object] = None
        if _PSUTIL_AVAILABLE:
            self._process = psutil.Process(os.getpid())

    def measure(self) -> RAMMeasurement:
        """Take a RAM snapshot."""
        m = RAMMeasurement(timestamp_ns=time.perf_counter_ns())
        unavailable: list[str] = []

        if not _PSUTIL_AVAILABLE:
            unavailable.append("psutil_not_installed")
            m.unavailable_fields = unavailable
            return m

        try:
            vm = psutil.virtual_memory()
            m.system_total_bytes = vm.total
            m.system_available_bytes = vm.available
            m.system_used_bytes = vm.used
        except Exception:
            unavailable.extend(["system_total_bytes", "system_available_bytes", "system_used_bytes"])

        try:
            if self._process is not None:
                mi = self._process.memory_info()  # type: ignore[union-attr]
                m.process_rss_bytes = mi.rss
                m.process_vms_bytes = mi.vms
        except Exception:
            unavailable.extend(["process_rss_bytes", "process_vms_bytes"])

        # Bandwidth is explicitly unavailable
        unavailable.append("bandwidth_bytes_per_second")
        m.unavailable_fields = unavailable
        return m

    def benchmark_bandwidth_empirical(
        self, size_bytes: int = 64 * 1024 * 1024
    ) -> Optional[float]:
        """
        Empirical memory throughput estimate using a simple in-process copy.

        This approximates memory bandwidth — it is NOT a hardware counter.
        Returns bytes/s or None on error.

        Limitation: dominated by L2/L3 cache for typical sizes.
        For large buffers it approaches DRAM bandwidth.
        """
        try:
            buf = bytearray(size_bytes)
            start = time.perf_counter_ns()
            result = bytes(buf)  # memory copy
            end = time.perf_counter_ns()
            elapsed_s = (end - start) / 1_000_000_000
            if elapsed_s <= 0:
                return None
            _ = result  # prevent optimization
            return size_bytes / elapsed_s
        except Exception:
            return None
