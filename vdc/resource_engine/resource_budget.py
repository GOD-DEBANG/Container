"""
src/vdc/resource_engine/resource_budget.py

Execution policies and resource budget specifications.
Defines LOW_CPU, BALANCED, and PERFORMANCE modes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ExecutionPolicy(str, Enum):
    LOW_CPU = "LOW_CPU"
    BALANCED = "BALANCED"
    PERFORMANCE = "PERFORMANCE"


@dataclass(frozen=True)
class ResourceBudget:
    policy: ExecutionPolicy
    concurrency_limit: int
    memory_reserve_bytes: int
    scheduling_interval_seconds: float
    target_throughput_bytes_per_sec: float
    pacing_delay_seconds: float

    @classmethod
    def from_policy(cls, policy: ExecutionPolicy = ExecutionPolicy.BALANCED) -> ResourceBudget:
        if policy == ExecutionPolicy.LOW_CPU:
            return cls(
                policy=ExecutionPolicy.LOW_CPU,
                concurrency_limit=1,
                memory_reserve_bytes=128 * 1024 * 1024,  # 128 MB reserve
                scheduling_interval_seconds=0.2,
                target_throughput_bytes_per_sec=5 * 1024 * 1024,  # 5 MB/s
                pacing_delay_seconds=0.01,
            )
        elif policy == ExecutionPolicy.PERFORMANCE:
            return cls(
                policy=ExecutionPolicy.PERFORMANCE,
                concurrency_limit=4,
                memory_reserve_bytes=32 * 1024 * 1024,   # 32 MB reserve
                scheduling_interval_seconds=0.02,
                target_throughput_bytes_per_sec=100 * 1024 * 1024, # 100 MB/s
                pacing_delay_seconds=0.0,
            )
        else:  # BALANCED default
            return cls(
                policy=ExecutionPolicy.BALANCED,
                concurrency_limit=2,
                memory_reserve_bytes=64 * 1024 * 1024,   # 64 MB reserve
                scheduling_interval_seconds=0.05,
                target_throughput_bytes_per_sec=25 * 1024 * 1024,  # 25 MB/s
                pacing_delay_seconds=0.002,
            )
