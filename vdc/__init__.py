"""
src/vdc

Virtual Container Dataset Generation Engine.
Self-contained, bounded-memory, lifecycle-managed execution engine.
Does not import FastAPI, Vercel-specific modules, or presentation code.
"""

from .container_core.virtual_container import VirtualContainer
from .container_core.factory import ContainerFactory
from .container_core.lifecycle import LifecycleManager
from .models.container_model import ContainerState
from .models.dataset_model import DatasetSpec, DatasetMetadata
from .models.execution_metrics import ExecutionMetrics, ExecutionReport
from .resource_engine.resource_budget import ExecutionPolicy, ResourceBudget
from .services.dataset_generation_service import DatasetGenerationService

__version__ = "0.1.0"

__all__ = [
    "VirtualContainer",
    "ContainerFactory",
    "LifecycleManager",
    "ContainerState",
    "DatasetSpec",
    "DatasetMetadata",
    "ExecutionMetrics",
    "ExecutionReport",
    "ExecutionPolicy",
    "ResourceBudget",
    "DatasetGenerationService",
]
