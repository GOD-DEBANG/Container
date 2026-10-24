"""
Self-Evolving AI/ML Research & Autonomous Learning Architecture
Scientific Specification & Configuration.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional


class FeedbackSignalType(str, Enum):
    RECONSTRUCTION_LOSS = "reconstruction_loss"
    LATENCY_REGRESSION = "latency_regression"
    CONTAINER_ANOMALY = "container_anomaly"
    DISTRIBUTION_DRIFT = "distribution_drift"
    VALIDATION_ACCURACY = "validation_accuracy"


@dataclass
class EvolutionConfig:
    generation: int = 1
    mutation_rate: float = 0.05
    adaptation_threshold: float = 0.15
    retraining_trigger_samples: int = 1000
    exploration_factor: float = 0.2
    active_learning_strategy: str = "uncertainty_entropy"


@dataclass
class ResearchConfig:
    experiment_id: str = "exp_self_evolving_v1"
    device: str = "auto"
    seed: int = 42
    data_dir: Path = Path(__file__).resolve().parent.parent / "data"
    checkpoints_dir: Path = Path(__file__).resolve().parent.parent / "artifacts" / "checkpoints"
    metrics_dir: Path = Path(__file__).resolve().parent.parent / "artifacts" / "metrics"
    evolution: EvolutionConfig = field(default_factory=EvolutionConfig)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "device": self.device,
            "seed": self.seed,
            "data_dir": str(self.data_dir),
            "checkpoints_dir": str(self.checkpoints_dir),
            "metrics_dir": str(self.metrics_dir),
            "evolution": {
                "generation": self.evolution.generation,
                "mutation_rate": self.evolution.mutation_rate,
                "adaptation_threshold": self.evolution.adaptation_threshold,
                "retraining_trigger_samples": self.evolution.retraining_trigger_samples,
                "exploration_factor": self.evolution.exploration_factor,
                "active_learning_strategy": self.evolution.active_learning_strategy,
            },
        }
