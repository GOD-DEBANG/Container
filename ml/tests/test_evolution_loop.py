"""
Unit & Integration Tests for Self-Evolving AI/ML Subsystem.
"""

import sys
from pathlib import Path
import pytest
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.configs.base_config import ResearchConfig
from ml.models.adaptive_classifier import AdaptiveClassifier
from ml.dataset.generator import AdaptiveDatasetSynthesizer
from ml.evolution.controller import AutonomousEvolutionLoop


def test_dataset_generator():
    synthesizer = AdaptiveDatasetSynthesizer()
    X, y, meta = synthesizer.generate_synthetic_telemetry_batch(n_samples=100, drift_factor=0.1)
    assert X.shape == (100, 5)
    assert len(y) == 100
    assert "feature_names" in meta


def test_model_capacity_evolution():
    model = AdaptiveClassifier(input_dim=5, hidden_dim=8, output_dim=2)
    initial_hidden = model.hidden_dim
    initial_version = model.architecture_version

    model.evolve_capacity(expand_factor=1.5)

    assert model.hidden_dim > initial_hidden
    assert model.architecture_version == initial_version + 1

    # Verify forward pass still functions after mutation
    X_dummy = np.random.randn(10, 5)
    probs, _ = model.forward(X_dummy)
    assert probs.shape == (10, 2)
    assert np.allclose(np.sum(probs, axis=1), 1.0)


def test_autonomous_evolution_cycle():
    config = ResearchConfig(experiment_id="unit_test_run", seed=999)
    loop = AutonomousEvolutionLoop(config=config)
    res = loop.run_evolution_cycle(generations=2)

    assert res["status"] == "completed"
    assert res["total_generations"] == 2
    assert len(res["history"]) == 2
