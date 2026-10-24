"""
src/vdc/resource_engine/resource_monitor.py

Hardware resource monitor using real OS instrumentation via psutil.
Detects whether hard OS-level CPU cgroup/job-object enforcement is active.
"""

from __future__ import annotations

import os
import sys
import time
import psutil

from ..models.execution_metrics import ResourceSnapshot


class ResourceMonitor:
    @staticmethod
    def is_hard_cpu_enforcement_available() -> bool:
        """
        Check if hardware/OS-level CPU quota throttling is strictly enforceable.
        On standard Linux with cgroups v1/v2 cpu.max / cpu.cfs_quota_us, returns True.
        On standard Windows or unconfigured Docker/Serverless runtimes, returns False.
        """
        if sys.platform.startswith("linux"):
            # Check for cgroups v2 cpu.max
            cgroup_v2_cpu = "/sys/fs/cgroup/cpu.max"
            if os.path.exists(cgroup_v2_cpu):
                try:
                    with open(cgroup_v2_cpu, "r") as f:
                        line = f.read().strip()
                        quota, period = line.split()
                        return quota != "max"
                except Exception:
                    pass
            # Check for cgroups v1 quota
            cgroup_v1_quota = "/sys/fs/cgroup/cpu/cpu.cfs_quota_us"
            if os.path.exists(cgroup_v1_quota):
                try:
                    with open(cgroup_v1_quota, "r") as f:
                        val = int(f.read().strip())
                        return val > 0
                except Exception:
                    pass
        return False

    @classmethod
    def take_snapshot(cls) -> ResourceSnapshot:
        """Capture instantaneous resource snapshot using psutil."""
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(os.getcwd())
        # Non-blocking cpu percent
        cpu_p = psutil.cpu_percent(interval=None)

        return ResourceSnapshot(
            timestamp=time.time(),
            cpu_percent=cpu_p,
            ram_used_bytes=mem.used,
            ram_available_bytes=mem.available,
            disk_available_bytes=disk.free,
            hard_cpu_enforcement_available=cls.is_hard_cpu_enforcement_available(),
        )
