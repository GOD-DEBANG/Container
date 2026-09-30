"""
cpu_engine/cpu_detector.py

Detects actual CPU hardware characteristics using psutil and os module.
Reports unavailability honestly when hardware counters are inaccessible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False


@dataclass
class CPUInfo:
    """Static CPU hardware information."""
    physical_cores: Optional[int] = None
    logical_cores: Optional[int] = None
    max_freq_hz: Optional[float] = None
    current_freq_hz: Optional[float] = None
    architecture: str = ""
    brand: str = ""
    unavailable_fields: list[str] = field(default_factory=list)

    @property
    def psutil_available(self) -> bool:
        return _PSUTIL_AVAILABLE


class CPUDetector:
    """Detects CPU characteristics from the host operating system."""

    @staticmethod
    def detect() -> CPUInfo:
        import platform
        info = CPUInfo()
        unavailable: list[str] = []

        info.architecture = platform.machine()

        if not _PSUTIL_AVAILABLE:
            unavailable.append("psutil_not_installed")
            info.unavailable_fields = unavailable
            return info

        try:
            info.physical_cores = psutil.cpu_count(logical=False)
        except Exception:
            unavailable.append("physical_cores")

        try:
            info.logical_cores = psutil.cpu_count(logical=True)
        except Exception:
            unavailable.append("logical_cores")

        try:
            freq = psutil.cpu_freq()
            if freq is not None:
                info.current_freq_hz = freq.current * 1_000_000
                info.max_freq_hz = freq.max * 1_000_000 if freq.max else None
            else:
                unavailable.extend(["current_freq_hz", "max_freq_hz"])
        except Exception:
            unavailable.extend(["current_freq_hz", "max_freq_hz"])

        # Brand string (Linux /proc/cpuinfo, Windows registry)
        brand = CPUDetector._get_brand()
        info.brand = brand or "unavailable"
        if not brand:
            unavailable.append("cpu_brand")

        info.unavailable_fields = unavailable
        return info

    @staticmethod
    def _get_brand() -> Optional[str]:
        try:
            import platform
            return platform.processor() or None
        except Exception:
            return None
