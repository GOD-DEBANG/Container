"""
mathematics/io_formula.py

Storage I/O throughput limit:

    V_IO(t) = 8 * B_IO_effective(t) / r_IO(t)

where:
    B_IO_effective = effective storage bandwidth (bytes/s),
                     calculated from measured read/write throughput
                     using a workload-specific blending model.
    r_IO           = storage bytes transferred per processed data bit.

For workloads that both read source data and write output data the
effective I/O bandwidth is modelled as the harmonic mean of read and
write bandwidth weighted by the fraction of time spent on each.

This avoids the common error of assuming nominal disk specifications
equal actual application throughput.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class IOThroughputResult:
    read_bandwidth_bytes_per_second: float
    write_bandwidth_bytes_per_second: float
    effective_bandwidth_bytes_per_second: float   # B_IO_effective
    bytes_per_bit: float                          # r_IO
    throughput_bits_per_second: float             # V_IO
    methodology: str = ""
    available: bool = True
    reason: str = ""


class IOThroughputFormula:
    """
    Calculates V_IO = 8 * B_IO_effective / r_IO.

    The blending model is intentionally simple and clearly documented
    so researchers can substitute a more accurate model.
    """

    @staticmethod
    def calculate(
        read_bandwidth_bps: float,
        write_bandwidth_bps: float,
        bytes_per_bit: float,
        read_fraction: float = 0.5,
    ) -> IOThroughputResult:
        """
        Calculate V_IO.

        read_fraction: fraction of I/O time spent reading (vs writing).
                       0.5 = equal read/write workload.
                       Caller should supply a workload-appropriate value.
        """
        if bytes_per_bit <= 0:
            return IOThroughputResult(
                read_bandwidth_bytes_per_second=read_bandwidth_bps,
                write_bandwidth_bytes_per_second=write_bandwidth_bps,
                effective_bandwidth_bytes_per_second=0.0,
                bytes_per_bit=bytes_per_bit,
                throughput_bits_per_second=0.0,
                available=False,
                reason=f"bytes_per_bit must be > 0, got {bytes_per_bit}",
            )

        rf = max(0.0, min(1.0, read_fraction))
        wf = 1.0 - rf

        # Effective bandwidth: weighted harmonic mean (safe against zeros)
        if read_bandwidth_bps > 0 and write_bandwidth_bps > 0:
            # Harmonic mean: 1 / (rf/R + wf/W)
            denominator = rf / read_bandwidth_bps + wf / write_bandwidth_bps
            effective = 1.0 / denominator if denominator > 0 else 0.0
            methodology = (
                f"harmonic mean: read_frac={rf:.2f}, write_frac={wf:.2f}"
            )
        elif read_bandwidth_bps > 0:
            effective = read_bandwidth_bps
            methodology = "read-only workload"
        elif write_bandwidth_bps > 0:
            effective = write_bandwidth_bps
            methodology = "write-only workload"
        else:
            return IOThroughputResult(
                read_bandwidth_bytes_per_second=read_bandwidth_bps,
                write_bandwidth_bytes_per_second=write_bandwidth_bps,
                effective_bandwidth_bytes_per_second=0.0,
                bytes_per_bit=bytes_per_bit,
                throughput_bits_per_second=0.0,
                available=False,
                reason="Both read and write bandwidth are 0 or unavailable",
            )

        throughput = (8.0 * effective) / bytes_per_bit
        return IOThroughputResult(
            read_bandwidth_bytes_per_second=read_bandwidth_bps,
            write_bandwidth_bytes_per_second=write_bandwidth_bps,
            effective_bandwidth_bytes_per_second=effective,
            bytes_per_bit=bytes_per_bit,
            throughput_bits_per_second=throughput,
            methodology=methodology,
        )
