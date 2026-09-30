"""
resource_engine/resource_budget.py

Configuration object for resource limits per container.

A ResourceBudget defines the allowed resource envelope for one
container execution. It does not enforce anything by itself —
ResourceAdmission and ResourceEnforcer consume it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class ExecutionPolicy(Enum):
    """Controls how aggressively the engine uses available resources."""
    PERFORMANCE = auto()    # use all available resources
    BALANCED = auto()       # moderate resource use
    LOW_CPU = auto()        # minimal CPU use, longer completion time
    RESOURCE_LIMITED = auto()  # strict budget enforcement


_POLICY_DEFAULTS: dict[ExecutionPolicy, dict[str, object]] = {
    ExecutionPolicy.PERFORMANCE: {
        "cpu_budget_cores": 0,          # 0 = all available
        "max_workers": 0,               # 0 = cpu_count
        "ram_budget_bytes": 0,          # 0 = 80% of system RAM
        "max_queue_depth": 256,
    },
    ExecutionPolicy.BALANCED: {
        "cpu_budget_cores": 0,
        "max_workers": 0,
        "ram_budget_bytes": 0,
        "max_queue_depth": 64,
    },
    ExecutionPolicy.LOW_CPU: {
        "cpu_budget_cores": 1,
        "max_workers": 1,
        "ram_budget_bytes": 0,
        "max_queue_depth": 8,
    },
    ExecutionPolicy.RESOURCE_LIMITED: {
        "cpu_budget_cores": 1,
        "max_workers": 2,
        "ram_budget_bytes": 256 * 1024 * 1024,  # 256 MiB
        "max_queue_depth": 16,
    },
}


@dataclass
class ResourceBudget:
    """
    Resource limits for one container execution.

    cpu_budget_cores: Number of CPU cores the engine may use.
                      0 = use all available logical cores.
    max_workers:      Maximum concurrent worker processes/threads.
                      0 = cpu_count.
    ram_budget_bytes: Maximum process RSS. 0 = 80% of system RAM.
    max_queue_depth:  Maximum depth of the bounded task queue.
    policy:           Which execution policy generated this budget.
    """

    cpu_budget_cores: float = 0.0
    max_workers: int = 0
    ram_budget_bytes: int = 0
    max_queue_depth: int = 64
    policy: ExecutionPolicy = ExecutionPolicy.BALANCED

    @classmethod
    def from_policy(
        cls,
        policy: ExecutionPolicy,
        cpu_override: float = 0.0,
        workers_override: int = 0,
        ram_override: int = 0,
    ) -> "ResourceBudget":
        """Create a budget from a named policy with optional overrides."""
        defaults = _POLICY_DEFAULTS[policy]
        return cls(
            cpu_budget_cores=cpu_override or float(defaults["cpu_budget_cores"]),  # type: ignore
            max_workers=workers_override or int(defaults["max_workers"]),  # type: ignore
            ram_budget_bytes=ram_override or int(defaults["ram_budget_bytes"]),  # type: ignore
            max_queue_depth=int(defaults["max_queue_depth"]),  # type: ignore
            policy=policy,
        )

    def effective_workers(self, available_cores: int) -> int:
        """Resolve max_workers = 0 to available_cores."""
        if self.max_workers > 0:
            return self.max_workers
        return max(1, available_cores)

    def effective_cpu_cores(self, available_cores: float) -> float:
        """Resolve cpu_budget_cores = 0 to available_cores."""
        if self.cpu_budget_cores > 0:
            return min(self.cpu_budget_cores, available_cores)
        return available_cores

    def effective_ram_bytes(self, system_total_bytes: int) -> int:
        """Resolve ram_budget_bytes = 0 to 80% of system RAM."""
        if self.ram_budget_bytes > 0:
            return self.ram_budget_bytes
        return int(system_total_bytes * 0.80)
