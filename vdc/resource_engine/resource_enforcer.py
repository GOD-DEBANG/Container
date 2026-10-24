"""
src/vdc/resource_engine/resource_enforcer.py

Translates mathematical throughput decisions into actual enforceable work budgets,
concurrency limits, and pacing sleep intervals.
"""

from __future__ import annotations

import time

from ..mathematics.throughput_formula import ThroughputDecision


class ResourceEnforcer:
    def __init__(self, scheduling_interval_seconds: float = 0.05) -> None:
        self.interval = scheduling_interval_seconds

    def calculate_interval_byte_budget(self, decision: ThroughputDecision) -> int:
        """
        Convert effective throughput (B/s) into a byte budget for the current scheduling interval:
            budget = floor(V_actual * interval)
        """
        budget = int(decision.actual_throughput_bps * self.interval)
        return max(4096, budget)

    def enforce_pacing(self, pacing_delay_seconds: float) -> None:
        """Apply pacing delay to limit CPU saturation."""
        if pacing_delay_seconds > 0.0:
            time.sleep(pacing_delay_seconds)
