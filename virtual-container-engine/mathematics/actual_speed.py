"""
mathematics/actual_speed.py

Implements the central execution control equation:

    V_actual(t) = min[V_d(t), V_CPU(t), V_RAM(t), V_IO(t)]

With optional runtime limit:

    V_actual(t) = min[V_d(t), V_CPU(t), V_RAM(t), V_IO(t), V_runtime(t)]

All inputs and the output are in bits per second of the same defined
workload, ensuring dimensional consistency.

If a resource limit is unavailable, the policy decides whether to
treat it as unconstrained (skip it) or to block execution.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class UnavailablePolicy(Enum):
    """How to handle a resource limit that could not be measured."""
    SKIP = auto()       # Treat as unconstrained (optimistic)
    BLOCK = auto()      # Treat as zero — block execution (conservative)
    WARN = auto()       # Treat as unconstrained but record a warning


@dataclass
class SpeedInput:
    """Named throughput limit input for one resource."""
    name: str
    bits_per_second: Optional[float]  # None = unavailable


@dataclass
class SpeedCalculationResult:
    """
    Result of V_actual = min(V_d, V_CPU, V_RAM, V_IO, ...).
    """
    actual_speed_bits_per_second: float
    limiting_resource: str          # name of the resource that set the limit
    inputs: list[SpeedInput]        # all inputs used in calculation
    skipped_resources: list[str]    # resources with unavailable measurements
    calculation_timestamp_ns: int   # time.perf_counter_ns() at calculation
    measurement_confidence: str     # "high" | "medium" | "low" | "estimate"
    measurement_type: str           # "realtime" | "cached" | "benchmark"
    policy_applied: str             # which UnavailablePolicy was used


class ActualSpeedCalculator:
    """
    Stateless calculator for V_actual(t) = min(...).

    This is the mathematical decision rule of the execution engine.
    The result must be consumed by the execution controller to make
    real scheduling decisions — it must not merely be logged.
    """

    def __init__(self, policy: UnavailablePolicy = UnavailablePolicy.SKIP) -> None:
        self._policy = policy

    def calculate(
        self,
        desired_speed_bps: float,
        cpu_limit_bps: Optional[float],
        ram_limit_bps: Optional[float],
        io_limit_bps: Optional[float],
        runtime_limit_bps: Optional[float] = None,
    ) -> SpeedCalculationResult:
        """
        Evaluate V_actual = min(all available limits).

        Parameters are in bits per second.
        Pass None for any limit that could not be measured.
        """
        inputs: list[SpeedInput] = [
            SpeedInput("desired", desired_speed_bps),
            SpeedInput("cpu", cpu_limit_bps),
            SpeedInput("ram", ram_limit_bps),
            SpeedInput("io", io_limit_bps),
        ]
        if runtime_limit_bps is not None:
            inputs.append(SpeedInput("runtime", runtime_limit_bps))

        skipped: list[str] = []
        candidates: list[tuple[float, str]] = []  # (value, name)

        for inp in inputs:
            if inp.bits_per_second is None:
                skipped.append(inp.name)
                if self._policy == UnavailablePolicy.BLOCK:
                    candidates.append((0.0, inp.name))
                # SKIP / WARN: exclude from min
            else:
                candidates.append((inp.bits_per_second, inp.name))

        if not candidates:
            # Nothing available — return 0 to block execution
            return SpeedCalculationResult(
                actual_speed_bits_per_second=0.0,
                limiting_resource="all_unavailable",
                inputs=inputs,
                skipped_resources=skipped,
                calculation_timestamp_ns=time.perf_counter_ns(),
                measurement_confidence="low",
                measurement_type="none",
                policy_applied=self._policy.name,
            )

        min_val, min_name = min(candidates, key=lambda x: x[0])

        # Confidence is high when all inputs are available
        if not skipped:
            confidence = "high"
        elif len(skipped) == 1:
            confidence = "medium"
        else:
            confidence = "low"

        return SpeedCalculationResult(
            actual_speed_bits_per_second=max(0.0, min_val),
            limiting_resource=min_name,
            inputs=inputs,
            skipped_resources=skipped,
            calculation_timestamp_ns=time.perf_counter_ns(),
            measurement_confidence=confidence,
            measurement_type="realtime",
            policy_applied=self._policy.name,
        )
