"""
resource_engine/cpu_unit.py

Actual CPU resource measurement using psutil.

Measures:
  - Physical and logical core counts
  - CPU frequency (current, min, max) if available
  - System-wide CPU utilization
  - Per-process CPU utilization
  - Process CPU quota (cgroup v2 on Linux where available)
  - Effective CPU capacity

Reports unavailability explicitly rather than fabricating values.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False


@dataclass
class CPUMeasurement:
    """
    Snapshot of CPU state at a point in time.
    All fields are Optional — None means measurement unavailable.
    """
    timestamp_ns: int = 0

    # Core counts
    physical_cores: Optional[int] = None
    logical_cores: Optional[int] = None

    # Frequency (Hz)
    current_freq_hz: Optional[float] = None
    max_freq_hz: Optional[float] = None

    # Utilization [0.0, 100.0]
    system_cpu_percent: Optional[float] = None
    process_cpu_percent: Optional[float] = None

    # Quota (CPU-core equivalents)
    quota_cores: Optional[float] = None          # from cgroup or OS config
    effective_capacity_cores: Optional[float] = None

    # Unavailability notes
    unavailable_fields: list[str] = field(default_factory=list)

    @property
    def psutil_available(self) -> bool:
        return _PSUTIL_AVAILABLE

    @property
    def effective_freq_hz(self) -> Optional[float]:
        """Best available frequency estimate."""
        return self.current_freq_hz or self.max_freq_hz


class CPUUnit:
    """
    Measures actual CPU resources available to this process.

    Limitations that are honestly reported:
      - Python worker-count limits do NOT provide hard OS CPU quotas.
      - CPU percent readings from psutil have a sampling window and may
        not capture very short bursts.
      - cgroup v2 quota detection is Linux-only.
    """

    # Sampling interval for cpu_percent (seconds). Shorter = less accurate.
    _CPU_PERCENT_INTERVAL: float = 0.1

    def __init__(self) -> None:
        self._process: Optional[object] = None
        if _PSUTIL_AVAILABLE:
            self._process = psutil.Process(os.getpid())

    def measure(self) -> CPUMeasurement:
        """Take a CPU snapshot. All fields may be None if unavailable."""
        m = CPUMeasurement(timestamp_ns=time.perf_counter_ns())
        unavailable: list[str] = []

        if not _PSUTIL_AVAILABLE:
            unavailable.append("psutil_not_installed")
            m.unavailable_fields = unavailable
            return m

        # Core counts
        try:
            m.physical_cores = psutil.cpu_count(logical=False)
        except Exception:
            unavailable.append("physical_cores")

        try:
            m.logical_cores = psutil.cpu_count(logical=True)
        except Exception:
            unavailable.append("logical_cores")

        # Frequency
        try:
            freq = psutil.cpu_freq()
            if freq is not None:
                m.current_freq_hz = freq.current * 1_000_000  # MHz → Hz
                m.max_freq_hz = freq.max * 1_000_000 if freq.max else None
            else:
                unavailable.append("cpu_freq")
        except Exception:
            unavailable.append("cpu_freq")

        # System utilization (non-blocking, may return 0.0 on first call)
        try:
            m.system_cpu_percent = psutil.cpu_percent(interval=None)
        except Exception:
            unavailable.append("system_cpu_percent")

        # Process utilization
        try:
            if self._process is not None:
                m.process_cpu_percent = self._process.cpu_percent(interval=None)
        except Exception:
            unavailable.append("process_cpu_percent")

        # cgroup v2 CPU quota (Linux only)
        quota = self._detect_cgroup_quota()
        if quota is not None:
            m.quota_cores = quota
        else:
            unavailable.append("cgroup_quota")

        # Effective capacity
        if m.quota_cores is not None:
            m.effective_capacity_cores = m.quota_cores
        elif m.logical_cores is not None:
            m.effective_capacity_cores = float(m.logical_cores)
        else:
            unavailable.append("effective_capacity_cores")

        m.unavailable_fields = unavailable
        return m

    def warm_up(self) -> None:
        """
        psutil cpu_percent() returns 0 on its first call (no baseline).
        Call this once before taking measurements.
        """
        if _PSUTIL_AVAILABLE:
            psutil.cpu_percent(interval=None)
            if self._process is not None:
                self._process.cpu_percent(interval=None)  # type: ignore[union-attr]
            time.sleep(self._CPU_PERCENT_INTERVAL)

    @staticmethod
    def _detect_cgroup_quota() -> Optional[float]:
        """
        Detect CPU quota from Linux cgroup v2.
        Returns cores (float) or None if unavailable/not on Linux.
        """
        quota_path = Path("/sys/fs/cgroup/cpu.max")
        if not quota_path.exists():
            return None
        try:
            text = quota_path.read_text().strip()
            parts = text.split()
            if len(parts) != 2:
                return None
            quota_str, period_str = parts
            if quota_str == "max":
                return None  # No quota set
            quota_us = float(quota_str)
            period_us = float(period_str)
            if period_us <= 0:
                return None
            return quota_us / period_us  # cores
        except Exception:
            return None
