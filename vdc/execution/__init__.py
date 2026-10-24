"""
src/vdc/execution

Execution engine and adaptive mathematical scheduling.
"""

from .backend import ExecutionBackend
from .scheduler import AdaptiveScheduler

__all__ = [
    "ExecutionBackend",
    "AdaptiveScheduler",
]
