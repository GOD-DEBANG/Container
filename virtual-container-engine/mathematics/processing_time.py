"""
mathematics/processing_time.py

Estimates processing time from throughput and dataset size.

    T_estimated = (8 * dataset_bytes) / V_actual   (seconds)

This is a planning estimate only — actual elapsed time is always
measured with time.perf_counter_ns() and reported separately.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProcessingTimeEstimate:
    dataset_bytes: int
    throughput_bits_per_second: float
    estimated_seconds: float
    available: bool = True
    reason: str = ""


class ProcessingTimeEstimator:
    """Estimates expected processing duration from throughput and size."""

    @staticmethod
    def estimate(
        dataset_bytes: int,
        throughput_bits_per_second: float,
    ) -> ProcessingTimeEstimate:
        """
        T = (8 * B) / V_actual.

        Returns unavailable if throughput is zero or negative.
        """
        if throughput_bits_per_second <= 0:
            return ProcessingTimeEstimate(
                dataset_bytes=dataset_bytes,
                throughput_bits_per_second=throughput_bits_per_second,
                estimated_seconds=0.0,
                available=False,
                reason=(
                    f"throughput_bits_per_second must be > 0, "
                    f"got {throughput_bits_per_second}"
                ),
            )
        if dataset_bytes <= 0:
            return ProcessingTimeEstimate(
                dataset_bytes=dataset_bytes,
                throughput_bits_per_second=throughput_bits_per_second,
                estimated_seconds=0.0,
                available=False,
                reason=f"dataset_bytes must be > 0, got {dataset_bytes}",
            )

        estimated = (dataset_bytes * 8) / throughput_bits_per_second
        return ProcessingTimeEstimate(
            dataset_bytes=dataset_bytes,
            throughput_bits_per_second=throughput_bits_per_second,
            estimated_seconds=estimated,
        )
