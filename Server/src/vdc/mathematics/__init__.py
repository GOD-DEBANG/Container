"""
src/vdc/mathematics

Pure computational mathematics formulas for dataset generation,
hierarchical allocation, resource-aware throughput, progress integration,
and completion validation.
"""

from .dataset_size import estimate_dataset_size, calculate_actual_size
from .allocation_formula import hierarchical_allocation, weighted_allocation
from .throughput_formula import (
    calculate_effective_throughput,
    calculate_measured_throughput,
    ThroughputDecision,
)
from .progress_integrator import (
    integrate_variable_throughput,
    calculate_remaining_bytes,
    calculate_progress_ratio,
)
from .completion_formula import validate_completion, CompletionReport

__all__ = [
    "estimate_dataset_size",
    "calculate_actual_size",
    "hierarchical_allocation",
    "weighted_allocation",
    "calculate_effective_throughput",
    "calculate_measured_throughput",
    "ThroughputDecision",
    "integrate_variable_throughput",
    "calculate_remaining_bytes",
    "calculate_progress_ratio",
    "validate_completion",
    "CompletionReport",
]
