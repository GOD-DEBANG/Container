"""
resource_engine/resource_admission.py

Admission control: decides whether a new unit of work can be started
given current resource state and configured budgets.

Checks:
  1. Active worker count <= max_workers
  2. Queue depth <= max_queue_depth
  3. Estimated next RAM usage <= ram_budget
  4. CPU quota not exhausted (best-effort application-level check)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from resource_engine.resource_snapshot import ResourceSnapshot
from resource_engine.resource_budget import ResourceBudget
from mathematics.ram_formula import RAMAdmissionFormula


@dataclass
class AdmissionResult:
    admitted: bool
    reasons_denied: list[str] = field(default_factory=list)
    active_workers: int = 0
    max_workers: int = 0
    queue_depth: int = 0
    process_ram_bytes: int = 0
    ram_budget_bytes: int = 0


class ResourceAdmission:
    """
    Gate that must be passed before scheduling new work.

    When admission is denied the caller MUST apply backpressure
    (wait or reduce concurrency) before retrying.
    """

    def __init__(self, budget: ResourceBudget) -> None:
        self._budget = budget

    def check(
        self,
        snapshot: ResourceSnapshot,
        estimated_next_bytes: int = 0,
        available_cores: int = 1,
        system_ram_bytes: int = 0,
    ) -> AdmissionResult:
        """
        Evaluate all admission conditions.

        estimated_next_bytes: estimated RAM that the next work unit will need.
        available_cores: number of cores available to this process.
        system_ram_bytes: total system RAM (for resolving 0-budget).
        """
        denied: list[str] = []
        max_workers = self._budget.effective_workers(available_cores)
        ram_budget = self._budget.effective_ram_bytes(
            system_ram_bytes or (8 * 1024 * 1024 * 1024)
        )

        # Worker count check
        if snapshot.active_workers >= max_workers:
            denied.append(
                f"active_workers={snapshot.active_workers} >= max_workers={max_workers}"
            )

        # Queue depth check
        if snapshot.queue_depth >= self._budget.max_queue_depth:
            denied.append(
                f"queue_depth={snapshot.queue_depth} >= max_queue_depth={self._budget.max_queue_depth}"
            )

        # RAM admission check
        process_ram = snapshot.ram.process_rss_bytes or 0
        ram_check = RAMAdmissionFormula.check_admission(
            m_used_bytes=process_ram,
            m_estimated_next_bytes=estimated_next_bytes,
            m_budget_bytes=ram_budget,
        )
        if not ram_check.admitted:
            denied.append(f"RAM: {ram_check.reason}")

        return AdmissionResult(
            admitted=len(denied) == 0,
            reasons_denied=denied,
            active_workers=snapshot.active_workers,
            max_workers=max_workers,
            queue_depth=snapshot.queue_depth,
            process_ram_bytes=process_ram,
            ram_budget_bytes=ram_budget,
        )
