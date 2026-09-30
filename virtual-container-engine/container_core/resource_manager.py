"""
container_core/resource_manager.py

Container-scoped wrapper for ResourceMonitor.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from resource_engine.resource_monitor import ResourceMonitor


class ResourceManager:
    """Provides resource monitoring for a container."""

    def __init__(self, temp_dir: Optional[Path] = None) -> None:
        self._monitor = ResourceMonitor(storage_path=temp_dir)

    @property
    def monitor(self) -> ResourceMonitor:
        return self._monitor

    def initialize(self) -> None:
        """Warm up benchmarks before processing starts."""
        self._monitor.warm_up()
