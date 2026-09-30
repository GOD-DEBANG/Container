"""
mathematics/ram_formula.py

RAM resource constraints:

  Admission condition:
      M_used(t) + M_estimated_next <= M_budget

  Memory-bandwidth throughput (bits/s):
      V_RAM(t) = 8 * B_RAM(t) / r_RAM(t)

  where:
      B_RAM   = effective memory bandwidth in bytes/s
      r_RAM   = memory bytes transferred per processed data bit

Note: Free RAM capacity (bytes) != processing throughput (bits/s).
These are distinct physical quantities and must never be confused.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RAMAdmissionResult:
    """Result of a RAM admission check."""
    m_used_bytes: int
    m_estimated_next_bytes: int
    m_budget_bytes: int
    admitted: bool
    reason: str = ""


@dataclass
class RAMThroughputResult:
    """V_RAM calculation result."""
    bandwidth_bytes_per_second: float  # B_RAM
    bytes_per_bit: float               # r_RAM
    throughput_bits_per_second: float  # V_RAM = 8*B_RAM / r_RAM
    available: bool = True
    reason: str = ""


class RAMAdmissionFormula:
    """
    Implements RAM admission and bandwidth-throughput calculations.

    Disclaimer: Actual memory bandwidth is very difficult to measure
    reliably in user space. Where not measurable, this is reported
    explicitly rather than substituting a fabricated constant.
    """

    @staticmethod
    def check_admission(
        m_used_bytes: int,
        m_estimated_next_bytes: int,
        m_budget_bytes: int,
    ) -> RAMAdmissionResult:
        """
        Evaluate: M_used(t) + M_estimated_next <= M_budget
        """
        projected = m_used_bytes + m_estimated_next_bytes
        admitted = projected <= m_budget_bytes
        reason = (
            "admitted"
            if admitted
            else (
                f"Projected usage {projected:,} B exceeds budget {m_budget_bytes:,} B"
            )
        )
        return RAMAdmissionResult(
            m_used_bytes=m_used_bytes,
            m_estimated_next_bytes=m_estimated_next_bytes,
            m_budget_bytes=m_budget_bytes,
            admitted=admitted,
            reason=reason,
        )

    @staticmethod
    def bandwidth_throughput(
        bandwidth_bytes_per_second: float,
        bytes_per_bit: float,
    ) -> RAMThroughputResult:
        """
        Calculate V_RAM = 8 * B_RAM / r_RAM.

        bandwidth_bytes_per_second: measured or estimated memory bandwidth
        bytes_per_bit: storage bytes moved per processed data bit
        """
        if bandwidth_bytes_per_second <= 0 or bytes_per_bit <= 0:
            return RAMThroughputResult(
                bandwidth_bytes_per_second=bandwidth_bytes_per_second,
                bytes_per_bit=bytes_per_bit,
                throughput_bits_per_second=0.0,
                available=False,
                reason=(
                    f"Invalid inputs: bandwidth={bandwidth_bytes_per_second}, "
                    f"bytes_per_bit={bytes_per_bit}"
                ),
            )
        throughput = (8.0 * bandwidth_bytes_per_second) / bytes_per_bit
        return RAMThroughputResult(
            bandwidth_bytes_per_second=bandwidth_bytes_per_second,
            bytes_per_bit=bytes_per_bit,
            throughput_bits_per_second=throughput,
        )
