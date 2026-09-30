"""
resource_engine/resource_limits.py

Defines hard and soft resource limits for the container engine.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ResourceLimits:
    """
    Hard resource ceiling for the entire engine (not per-container).

    These are the maximum values any container may request.
    Individual containers are further limited by ResourceBudget.
    """

    max_cpu_cores: float = 0.0           # 0 = all available
    max_ram_bytes: int = 0               # 0 = 80% of system RAM
    max_temp_disk_bytes: int = 0         # 0 = no limit
    max_concurrent_containers: int = 4

    def validate(self) -> None:
        if self.max_concurrent_containers < 1:
            raise ValueError("max_concurrent_containers must be >= 1")
