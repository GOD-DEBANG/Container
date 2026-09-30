"""
mathematics/cpu_formula.py

Implements the two CPU throughput models:

  Theoretical:
      V_CPU_theoretical(t) = F_budget(t) * eta_CPU(t) / C_b(t)

  where:
      F_budget  = effective CPU cycles per second (Hz)
      eta_CPU   = workload efficiency (0 < eta <= 1)
      C_b       = cycles per bit for the workload

  Empirical (measured):
      V_CPU_measured = 8 * B / T   (bits per second)

  where:
      B = bytes processed by benchmark
      T = elapsed seconds (from perf_counter_ns)

Both models are kept explicitly separate and labelled.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class TheoreticalCPUResult:
    f_budget_hz: float          # effective CPU cycles/s
    eta_cpu: float              # efficiency factor [0,1]
    cycles_per_bit: float       # C_b
    throughput_bits_per_second: float
    methodology: str = "theoretical: V = F_budget * eta / C_b"
    available: bool = True
    reason: str = ""


@dataclass
class MeasuredCPUResult:
    benchmark_bytes: int
    elapsed_ns: int
    throughput_bits_per_second: float
    methodology: str = "empirical: V = 8*B / T"
    available: bool = True
    reason: str = ""

    @property
    def elapsed_seconds(self) -> float:
        return self.elapsed_ns / 1_000_000_000


class CPUThroughputFormula:
    """
    Encapsulates CPU throughput calculations.

    Theoretical and measured results are always kept separate and
    labelled with their methodology so callers are never misled about
    the source of a value.
    """

    # Minimum sensible workload for a benchmark (64 KiB)
    MIN_BENCHMARK_BYTES: int = 65_536

    @staticmethod
    def theoretical(
        f_budget_hz: float,
        eta_cpu: float,
        cycles_per_bit: float,
    ) -> TheoreticalCPUResult:
        """
        Calculate V_CPU_theoretical = F_budget * eta_CPU / C_b.

        All three inputs must be positive. If they are not, returns an
        unavailable result rather than a fabricated number.
        """
        if f_budget_hz <= 0 or eta_cpu <= 0 or cycles_per_bit <= 0:
            return TheoreticalCPUResult(
                f_budget_hz=f_budget_hz,
                eta_cpu=eta_cpu,
                cycles_per_bit=cycles_per_bit,
                throughput_bits_per_second=0.0,
                available=False,
                reason=(
                    f"Invalid inputs: f_budget_hz={f_budget_hz}, "
                    f"eta_cpu={eta_cpu}, cycles_per_bit={cycles_per_bit}"
                ),
            )
        throughput = (f_budget_hz * eta_cpu) / cycles_per_bit
        return TheoreticalCPUResult(
            f_budget_hz=f_budget_hz,
            eta_cpu=eta_cpu,
            cycles_per_bit=cycles_per_bit,
            throughput_bits_per_second=throughput,
        )

    @staticmethod
    def measured(
        benchmark_bytes: int,
        elapsed_ns: int,
    ) -> MeasuredCPUResult:
        """
        Calculate V_CPU_measured = 8 * B / T.

        Uses actual measured elapsed time (perf_counter_ns).
        Returns unavailable if inputs are invalid.
        """
        if benchmark_bytes <= 0:
            return MeasuredCPUResult(
                benchmark_bytes=benchmark_bytes,
                elapsed_ns=elapsed_ns,
                throughput_bits_per_second=0.0,
                available=False,
                reason=f"benchmark_bytes must be > 0, got {benchmark_bytes}",
            )
        if elapsed_ns <= 0:
            return MeasuredCPUResult(
                benchmark_bytes=benchmark_bytes,
                elapsed_ns=elapsed_ns,
                throughput_bits_per_second=0.0,
                available=False,
                reason=f"elapsed_ns must be > 0, got {elapsed_ns}",
            )
        elapsed_s = elapsed_ns / 1_000_000_000
        throughput = (benchmark_bytes * 8) / elapsed_s
        return MeasuredCPUResult(
            benchmark_bytes=benchmark_bytes,
            elapsed_ns=elapsed_ns,
            throughput_bits_per_second=throughput,
        )
