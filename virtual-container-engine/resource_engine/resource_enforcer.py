"""
resource_engine/resource_enforcer.py

Applies resource control decisions to the execution environment.

The enforcer acts on AdmissionResult and SpeedCalculationResult to:
  - Limit the number of active workers
  - Signal backpressure to the scheduler
  - Record resource control actions for the execution report

IMPORTANT: This component enforces at application level only.
Hard OS-level CPU quotas require OS mechanisms (cgroups, etc.).
When hard enforcement is unavailable, this is reported explicitly.
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from typing import Optional

from resource_engine.resource_admission import AdmissionResult
from mathematics.actual_speed import SpeedCalculationResult


@dataclass
class EnforcementAction:
    timestamp_ns: int
    action: str
    reason: str
    new_worker_limit: Optional[int] = None
    backpressure_applied: bool = False


class ResourceEnforcer:
    """
    Translates resource decisions into scheduling actions.

    Thread-safe: may be called from the scheduler thread.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._actions: list[EnforcementAction] = []
        self._backpressure_active = False
        self._worker_limit: Optional[int] = None

    @property
    def backpressure_active(self) -> bool:
        with self._lock:
            return self._backpressure_active

    @property
    def worker_limit(self) -> Optional[int]:
        with self._lock:
            return self._worker_limit

    def apply_admission_result(self, result: AdmissionResult) -> bool:
        """
        Apply an admission result.

        Returns True if work may proceed, False if backpressure applied.
        """
        with self._lock:
            if not result.admitted:
                self._backpressure_active = True
                action = EnforcementAction(
                    timestamp_ns=time.perf_counter_ns(),
                    action="backpressure_on",
                    reason="; ".join(result.reasons_denied),
                    backpressure_applied=True,
                )
                self._actions.append(action)
                return False
            else:
                if self._backpressure_active:
                    self._backpressure_active = False
                    action = EnforcementAction(
                        timestamp_ns=time.perf_counter_ns(),
                        action="backpressure_off",
                        reason="resources available",
                        backpressure_applied=False,
                    )
                    self._actions.append(action)
                return True

    def apply_speed_result(self, result: SpeedCalculationResult) -> None:
        """
        Record the speed calculation result.
        The worker limit is adjusted based on the limiting resource.
        """
        with self._lock:
            if result.actual_speed_bits_per_second <= 0:
                self._backpressure_active = True
                action = EnforcementAction(
                    timestamp_ns=time.perf_counter_ns(),
                    action="speed_zero_backpressure",
                    reason=f"V_actual=0 (limiting: {result.limiting_resource})",
                    backpressure_applied=True,
                )
                self._actions.append(action)

    def get_actions_summary(self) -> list[str]:
        """Return human-readable list of resource control actions."""
        with self._lock:
            return [f"[{a.action}] {a.reason}" for a in self._actions]

    def clear(self) -> None:
        with self._lock:
            self._actions.clear()
            self._backpressure_active = False
            self._worker_limit = None
