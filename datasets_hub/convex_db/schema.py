"""
Scientific Dataset Schema Definitions & Convex Types.
Defines formal structures for container datasets, server telemetry, and evaluation runs.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
from enum import Enum


class DatasetModality(str, Enum):
    NUMERIC_TELEMETRY = "numeric_telemetry"
    CONTAINER_EXECUTION_TRACE = "container_execution_trace"
    SERVER_EVENT_STREAM = "server_event_stream"
    ANOMALY_BENCHMARK = "anomaly_benchmark"


@dataclass
class DatasetInputSpec:
    dataset_name: str
    target_records: int
    modality: DatasetModality
    drift_factor: float = 0.0
    anomaly_ratio: float = 0.05
    seed: int = 42
    custom_parameters: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["modality"] = self.modality.value
        return d
