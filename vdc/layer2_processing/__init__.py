"""
src/vdc/layer2_processing

Layer 2 processing package with bounded queues and deterministic generation.
"""

from .bounded_queue import BoundedWorkQueue
from .processor import DeterministicByteProcessor, SubchunkProcessingResult
from .worker_manager import ProcessingWorkerManager

__all__ = [
    "BoundedWorkQueue",
    "DeterministicByteProcessor",
    "SubchunkProcessingResult",
    "ProcessingWorkerManager",
]
