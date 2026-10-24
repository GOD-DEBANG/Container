# Scientific ML & AI Self-Evolving Engine

This directory houses the autonomous, self-evolving machine learning research environment integrated with the **Virtual Container Dataset Engine (`vdc`)**.

---

## 🏛️ Directory Structure & Scientific Topology

```text
Container/ml/
├── configs/                  # Experiment configurations, hyperparameters, & evolution policies
│   ├── __init__.py
│   └── base_config.py
├── connectors/               # Bidirectional telemetry & policy bridge to Virtual Container engine
│   ├── __init__.py
│   └── container_bridge.py
├── dataset/                  # Dataset synthesis, active sampling, & distribution shift generation
│   ├── __init__.py
│   └── generator.py
├── models/                   # Self-adaptive neural topologies with dynamic capacity evolution
│   ├── __init__.py
│   └── adaptive_classifier.py
├── training/                 # Dynamic trainers with momentum, early stopping, and loss diagnostics
│   ├── __init__.py
│   └── trainer.py
├── evolution/                # Closed-loop controller, architectural mutation, and drift monitors
│   ├── __init__.py
│   └── controller.py
├── experiments/              # Reproducible research scripts and benchmarking routines
│   └── run_evolution_experiment.py
├── tests/                    # Scientific unit tests verifying convergence and mutation integrity
│   └── test_evolution_loop.py
├── data/                     # Generated raw & processed datasets (reproducible seed checkpoints)
│   ├── raw/
│   └── processed/
└── artifacts/                # Serialized model weights, checkpoints, and telemetry logs
    ├── checkpoints/
    └── metrics/
```

---

## 🔄 Self-Evolving Closed Loop Workflow

1. **Telemetry Ingestion**: `ContainerMLBridge` connects to the Virtual Container engine to collect real-time system metrics (CPU, memory bounds, I/O rates, latency spikes).
2. **Drift Detection**: `AutonomousEvolutionLoop` computes statistical divergence metrics on incoming operational profiles.
3. **Adaptive Dataset Synthesis**: `AdaptiveDatasetSynthesizer` generates edge-case datasets targeting diagnosed container stress vectors.
4. **Architectural Mutation**: `AdaptiveClassifier.evolve_capacity()` dynamically expands neural capacity without forgetting previous distributions.
5. **Continuous Optimization**: `SelfEvolvingTrainer` retrains and evaluates candidate checkpoints.
6. **Policy Actuation**: Calibrated policies and threshold predictions are deployed back into the Virtual Container engine.

---

## 🚀 Running Experiments

Execute an autonomous evolution run:
```bash
python ml/experiments/run_evolution_experiment.py
```
