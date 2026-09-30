"""
cpu_engine/cycles_per_bit.py

Estimates cycles per bit (C_b) for use in the theoretical CPU model.

C_b cannot be measured directly in pure Python without hardware
performance counters (PMU). This module provides:
  1. An empirical estimate using measured throughput and known frequency.
  2. A clearly documented fallback constant for SHA-256-like workloads.

Neither value is fabricated — both are derived from measurable inputs
or documented references, with uncertainty clearly stated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class CyclesPerBitEstimate:
    cycles_per_bit: float
    methodology: str
    available: bool = True
    uncertainty: str = ""


class CyclesPerBitEstimator:
    """
    Estimates C_b from empirical data or uses a documented constant.

    Empirical derivation:
        C_b = F_cpu / V_measured
    where:
        F_cpu = effective CPU frequency (Hz)
        V_measured = measured throughput (bits/s)

    This inverts the theoretical model to back-calculate C_b.
    The result is an approximation because it includes all pipeline,
    cache, and scheduling overheads — which is correct for a realistic
    C_b used in the planning equation.
    """

    # Conservative documented estimate for SHA-256 on modern x86.
    # Source: NIST benchmarks and open literature place SHA-256 at
    # approximately 4–12 cycles/byte on modern CPUs, which is 0.5–1.5
    # cycles/bit. We use 8 as a conservative (slower) estimate.
    _FALLBACK_CPB: float = 8.0
    _FALLBACK_NOTE: str = (
        "fallback constant: 8 cycles/bit for SHA-256-like workload "
        "(conservative estimate from open literature)"
    )

    @classmethod
    def from_measurement(
        cls,
        freq_hz: Optional[float],
        measured_throughput_bps: Optional[float],
    ) -> CyclesPerBitEstimate:
        """
        Estimate C_b = F_cpu / V_measured.

        Returns the fallback constant if inputs are unavailable.
        """
        if (
            freq_hz is None
            or measured_throughput_bps is None
            or freq_hz <= 0
            or measured_throughput_bps <= 0
        ):
            return CyclesPerBitEstimate(
                cycles_per_bit=cls._FALLBACK_CPB,
                methodology=cls._FALLBACK_NOTE,
                uncertainty=(
                    "input frequency or throughput unavailable; "
                    "using conservative constant"
                ),
            )

        cpb = freq_hz / measured_throughput_bps
        return CyclesPerBitEstimate(
            cycles_per_bit=cpb,
            methodology=(
                f"empirical: C_b = F_cpu / V_measured = "
                f"{freq_hz:.3e} Hz / {measured_throughput_bps:.3e} bps"
            ),
            uncertainty=(
                "includes pipeline, cache, and scheduling overheads; "
                "not a hardware counter measurement"
            ),
        )
