"""
ML Package Initialization.
Exposes core self-evolving pipeline and connector components.
"""

from .configs.base_config import ResearchConfig, EvolutionConfig, FeedbackSignalType
from .connectors.container_bridge import ContainerMLBridge
from .dataset.generator import AdaptiveDatasetSynthesizer
from .training.trainer import SelfEvolvingTrainer
from .evolution.controller import AutonomousEvolutionLoop

__version__ = "0.1.0"

__all__ = [
    "ResearchConfig",
    "EvolutionConfig",
    "FeedbackSignalType",
    "ContainerMLBridge",
    "AdaptiveDatasetSynthesizer",
    "SelfEvolvingTrainer",
    "AutonomousEvolutionLoop",
]
