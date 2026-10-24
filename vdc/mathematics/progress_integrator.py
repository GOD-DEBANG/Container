"""
src/vdc/mathematics/progress_integrator.py

Numerical integration of varying throughput and remaining work calculations:
    S_processed(t) = integral(V_actual(tau), t0, t) d_tau
    remaining_bytes = max(0, target_bytes - actual_completed_bytes)
    progress_ratio = min(1.0, max(0.0, actual_completed_bytes / target_bytes))
"""

from __future__ import annotations

import math
from typing import Sequence, Tuple


def integrate_variable_throughput(samples: Sequence[Tuple[float, float]]) -> float:
    """
    Compute theoretical accumulated bytes from variable throughput observations
    using the Composite Trapezoidal Rule:
        Integral ~ sum_{i=0}^{N-2} 0.5 * (V_i + V_{i+1}) * (t_{i+1} - t_i)

    Args:
        samples: Chronologically sorted sequence of (t_i, V_i) tuples where:
                 t_i is timestamp in seconds (monotonic non-decreasing)
                 V_i is instantaneous throughput in bytes per second (>= 0).

    Returns:
        Numerically integrated byte volume (>= 0.0).

    Raises:
        ValueError: If fewer than 2 samples are provided, timestamps are not non-decreasing,
                    or values are negative/NaN/Inf.
    """
    if len(samples) < 2:
        return 0.0

    total_bytes = 0.0
    for i in range(len(samples) - 1):
        t1, v1 = samples[i]
        t2, v2 = samples[i + 1]

        for val, name in [(t1, "t1"), (v1, "v1"), (t2, "t2"), (v2, "v2")]:
            if not isinstance(val, (int, float)):
                raise ValueError(f"{name} must be numeric")
            if math.isnan(val) or math.isinf(val):
                raise ValueError(f"{name} cannot be NaN or Infinite")

        if v1 < 0.0 or v2 < 0.0:
            raise ValueError("Throughput sample rates cannot be negative")
        if t2 < t1:
            raise ValueError(f"Timestamps must be non-decreasing: t2 ({t2}) < t1 ({t1})")

        dt = float(t2 - t1)
        mean_v = 0.5 * (float(v1) + float(v2))
        total_bytes += mean_v * dt

    return max(0.0, total_bytes)


def calculate_remaining_bytes(target_bytes: int, actual_completed_bytes: int) -> int:
    """
    Calculate remaining bytes required to complete dataset:
        remaining = max(0, target_bytes - actual_completed_bytes)

    Raises:
        ValueError: If target_bytes <= 0 or actual_completed_bytes < 0.
    """
    if not isinstance(target_bytes, int) or target_bytes <= 0:
        raise ValueError(f"target_bytes must be positive integer, got {target_bytes}")
    if not isinstance(actual_completed_bytes, int) or actual_completed_bytes < 0:
        raise ValueError(f"actual_completed_bytes must be non-negative integer, got {actual_completed_bytes}")

    return max(0, target_bytes - actual_completed_bytes)


def calculate_progress_ratio(actual_completed_bytes: int, target_bytes: int) -> float:
    """
    Compute progress percentage ratio:
        progress = completed / target
    Guaranteed to be strictly bounded within [0.0, 1.0] (never exceeds 100%).

    Raises:
        ValueError: If target_bytes <= 0 or actual_completed_bytes < 0.
    """
    if not isinstance(target_bytes, int) or target_bytes <= 0:
        raise ValueError(f"target_bytes must be positive integer, got {target_bytes}")
    if not isinstance(actual_completed_bytes, int) or actual_completed_bytes < 0:
        raise ValueError(f"actual_completed_bytes must be non-negative integer, got {actual_completed_bytes}")

    ratio = float(actual_completed_bytes) / float(target_bytes)
    return min(1.0, max(0.0, ratio))
