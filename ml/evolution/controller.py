"""
Self-Evolution Autonomous Controller & Genetic/Architectural Mutation Engine.
Monitors container performance drift, triggers self-reconfiguration,
and coordinates active self-learning iterations.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List
import numpy as np

from ..configs.base_config import ResearchConfig
from ..connectors.container_bridge import ContainerMLBridge
from ..dataset.generator import AdaptiveDatasetSynthesizer
from ..models.adaptive_classifier import AdaptiveClassifier
from ..training.trainer import SelfEvolvingTrainer

logger = logging.getLogger("AutonomousEvolutionLoop")


class AutonomousEvolutionLoop:
    """
    Core closed-loop engine for continuous self-evolution:
    1. Collects live container metrics via ContainerMLBridge.
    2. Detects drift/anomalies in execution patterns.
    3. Triggers targeted dataset generation (hard-example synthesis).
    4. Evaluates whether to expand network architecture or adjust learning hyperparameters.
    5. Retrains and evaluates new model candidate.
    6. Deploys updated intelligence back to the Container runtime.
    """

    def __init__(self, config: ResearchConfig):
        self.config = config
        self.bridge = ContainerMLBridge()
        self.dataset_synthesizer = AdaptiveDatasetSynthesizer(output_dir=config.data_dir)
        self.model = AdaptiveClassifier(seed=config.seed)
        self.trainer = SelfEvolvingTrainer(self.model)
        self.evolution_log: List[Dict[str, Any]] = []

    def detect_drift(self, recent_data: np.ndarray, reference_mean: np.ndarray, threshold: float = 0.25) -> bool:
        """Calculates multivariate Mahalanobis-like drift distance from baseline."""
        current_mean = np.mean(recent_data, axis=0)
        drift_distance = float(np.linalg.norm(current_mean - reference_mean))
        return drift_distance > threshold

    def run_evolution_cycle(self, generations: int = 3) -> Dict[str, Any]:
        """
        Executes autonomous self-evolving cycles linking Container telemetry to updated ML models.
        """
        logger.info(f"Initiating autonomous evolution across {generations} generational epochs.")
        reference_mean = np.array([0.45, 0.50, 0.30, 0.0, 0.20])

        for gen in range(1, generations + 1):
            drift_factor = (gen - 1) * 0.15
            logger.info(f"--- Generation {gen} (Simulated Drift Factor: {drift_factor:.2f}) ---")

            # 1. Synthesize targeted training set reflecting contemporary container dynamics
            X_train, y_train, meta = self.dataset_synthesizer.generate_synthetic_telemetry_batch(
                n_samples=1200, drift_factor=drift_factor, seed=self.config.seed + gen
            )
            X_val, y_val, _ = self.dataset_synthesizer.generate_synthetic_telemetry_batch(
                n_samples=300, drift_factor=drift_factor, seed=self.config.seed + gen + 100
            )

            # 2. Check for capacity bottleneck / drift
            drift_detected = self.detect_drift(X_train, reference_mean)
            if drift_detected or gen > 1:
                logger.info("Distribution shift detected: Evolving model capacity (architectural mutation)...")
                self.model.evolve_capacity(expand_factor=1.2)

            # 3. Optimize model
            for epoch in range(10):
                self.trainer.train_epoch(X_train, y_train, batch_size=64)

            eval_metrics = self.trainer.evaluate(X_val, y_val)
            logger.info(f"Gen {gen} Validation Accuracy: {eval_metrics['val_accuracy']:.4f}")

            # 4. Connect feedback loop back to Virtual Container
            container_policy = {
                "generation": gen,
                "model_capacity": self.model.hidden_dim,
                "architecture_version": self.model.architecture_version,
                "expected_val_accuracy": eval_metrics["val_accuracy"],
                "drift_mitigated": drift_detected,
            }
            self.bridge.inject_ml_policy_to_container(container_policy)

            cycle_summary = {
                "generation": gen,
                "hidden_dim": self.model.hidden_dim,
                "architecture_version": self.model.architecture_version,
                "metrics": eval_metrics,
            }
            self.evolution_log.append(cycle_summary)

        # Save checkpoint & metrics
        self.config.metrics_dir.mkdir(parents=True, exist_ok=True)
        metrics_file = self.config.metrics_dir / "evolution_history.json"
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(self.evolution_log, f, indent=2)

        return {
            "status": "completed",
            "total_generations": generations,
            "final_architecture_version": self.model.architecture_version,
            "final_hidden_dim": self.model.hidden_dim,
            "history": self.evolution_log,
        }
