"""
Integration endpoint for Server: Exposes autonomous ML metrics, evolution triggers,
and allows Server components to query the self-evolving ML brain.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Any

# Walk up to find the root Container directory containing 'ml'
curr = Path(__file__).resolve()
REPO_ROOT = None
for parent in curr.parents:
    if (parent / "ml").exists() and (parent / "Server").exists():
        REPO_ROOT = parent
        break

if REPO_ROOT and str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.configs.base_config import ResearchConfig
from ml.evolution.controller import AutonomousEvolutionLoop


class ContainerMLEvolutionService:
    """
    Exposes self-evolving ML capabilities directly inside the Server application runtime.
    """

    def __init__(self):
        self.config = ResearchConfig(experiment_id="server_integrated_ml")
        self.loop = AutonomousEvolutionLoop(self.config)

    def trigger_self_evolution(self, generations: int = 1) -> Dict[str, Any]:
        """
        Triggers an on-demand self-evolution cycle from the Server.
        """
        return self.loop.run_evolution_cycle(generations=generations)

    def predict_container_anomaly(self, cpu: float, mem: float, io: float, latency: float, queue: float) -> int:
        """
        Queries the current active evolved model to predict container degradation.
        """
        import numpy as np
        X = np.array([[cpu, mem, io, latency, queue]])
        return int(self.loop.model.predict(X)[0])
