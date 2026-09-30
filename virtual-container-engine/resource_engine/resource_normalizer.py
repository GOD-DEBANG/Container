"""
resource_engine/resource_normalizer.py

Converts raw resource measurements into compatible throughput limits
(bits per second of the same defined workload) so they can be compared
by the ActualSpeedCalculator.

Unit normalization rule (per spec §7):
    min(CPU Hz, RAM GB, disk MB/s)  ← INVALID — different dimensions
    min(V_CPU bps, V_RAM bps, V_IO bps) ← VALID

Each resource adapter produces either:
  - A compatible throughput estimate (bps)
  - An explicit None (unavailable)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from resource_engine.resource_snapshot import ResourceSnapshot
from resource_engine.resource_budget import ResourceBudget
from mathematics.cpu_formula import CPUThroughputFormula
from mathematics.ram_formula import RAMAdmissionFormula
from mathematics.io_formula import IOThroughputFormula


@dataclass
class NormalizedLimits:
    """All resource limits expressed in bits/second for comparison."""
    cpu_limit_bps: Optional[float]       # None = unavailable
    ram_limit_bps: Optional[float]       # None = unavailable
    io_limit_bps: Optional[float]        # None = unavailable
    cpu_methodology: str = ""
    ram_methodology: str = ""
    io_methodology: str = ""


class ResourceNormalizer:
    """
    Converts a ResourceSnapshot + ResourceBudget into NormalizedLimits.

    All conversion formulas are documented in mathematics/.
    When a measurement is unavailable, the corresponding limit is None.
    """

    # Assumed cycles per bit for a SHA-256-based workload (conservative estimate).
    # This value is used only for theoretical CPU throughput; the measured
    # throughput from the benchmark is preferred when available.
    _DEFAULT_CYCLES_PER_BIT: float = 8.0

    # Efficiency factor — accounts for scheduling overhead, cache misses, etc.
    _DEFAULT_ETA: float = 0.75

    # r_RAM: memory bytes moved per processed data bit.
    # For a streaming copy workload, ~1 byte read + ~1 byte write per 8 data bits.
    _RAM_BYTES_PER_BIT: float = 2.0 / 8.0  # = 0.25

    # r_IO: storage bytes per processed data bit (read source + write output)
    _IO_BYTES_PER_BIT: float = 2.0 / 8.0   # = 0.25

    def __init__(self, budget: ResourceBudget) -> None:
        self._budget = budget

    def normalize(
        self,
        snapshot: ResourceSnapshot,
        measured_cpu_bps: Optional[float] = None,
        ram_bandwidth_bps: Optional[float] = None,
    ) -> NormalizedLimits:
        """
        Produce NormalizedLimits from a snapshot.

        measured_cpu_bps: If available, use empirical CPU throughput directly.
        ram_bandwidth_bps: If available, use empirical RAM bandwidth.
        """
        cpu_limit = self._cpu_limit(snapshot, measured_cpu_bps)
        ram_limit = self._ram_limit(snapshot, ram_bandwidth_bps)
        io_limit = self._io_limit(snapshot)

        return NormalizedLimits(
            cpu_limit_bps=cpu_limit[0],
            ram_limit_bps=ram_limit[0],
            io_limit_bps=io_limit[0],
            cpu_methodology=cpu_limit[1],
            ram_methodology=ram_limit[1],
            io_methodology=io_limit[1],
        )

    def _cpu_limit(
        self,
        snapshot: ResourceSnapshot,
        measured_bps: Optional[float],
    ) -> tuple[Optional[float], str]:
        # Prefer measured workload throughput
        if measured_bps is not None and measured_bps > 0:
            # Scale by budget fraction of available cores
            capacity = snapshot.cpu.effective_capacity_cores or 1.0
            budget_fraction = min(
                self._budget.cpu_budget_cores / capacity, 1.0
            )
            scaled = measured_bps * budget_fraction
            return scaled, "measured: scaled by cpu_budget fraction"

        # Fall back to theoretical model
        freq = snapshot.cpu.effective_freq_hz
        capacity = snapshot.cpu.effective_capacity_cores
        if freq is None or capacity is None:
            return None, "unavailable: cpu_freq or capacity missing"

        budget_cores = min(self._budget.cpu_budget_cores, capacity)
        f_budget = budget_cores * freq
        result = CPUThroughputFormula.theoretical(
            f_budget_hz=f_budget,
            eta_cpu=self._DEFAULT_ETA,
            cycles_per_bit=self._DEFAULT_CYCLES_PER_BIT,
        )
        if not result.available:
            return None, result.reason
        return result.throughput_bits_per_second, result.methodology

    def _ram_limit(
        self,
        snapshot: ResourceSnapshot,
        bandwidth_bps: Optional[float],
    ) -> tuple[Optional[float], str]:
        if bandwidth_bps is not None and bandwidth_bps > 0:
            result = RAMAdmissionFormula.bandwidth_throughput(
                bandwidth_bytes_per_second=bandwidth_bps,
                bytes_per_bit=self._RAM_BYTES_PER_BIT,
            )
            if result.available:
                return result.throughput_bits_per_second, "empirical RAM bandwidth"
        return None, "unavailable: memory bandwidth not measurable in pure Python"

    def _io_limit(
        self,
        snapshot: ResourceSnapshot,
    ) -> tuple[Optional[float], str]:
        read_bps = snapshot.storage.read_bandwidth_bytes_per_second
        write_bps = snapshot.storage.write_bandwidth_bytes_per_second
        if read_bps is None and write_bps is None:
            return None, "unavailable: storage benchmark not run"
        result = IOThroughputFormula.calculate(
            read_bandwidth_bps=read_bps or 0.0,
            write_bandwidth_bps=write_bps or 0.0,
            bytes_per_bit=self._IO_BYTES_PER_BIT,
            read_fraction=0.5,
        )
        if not result.available:
            return None, result.reason
        return result.throughput_bits_per_second, result.methodology
