"""
Adaptive Dataset Synthesizer and Curator.
Creates, augments, and dynamically balances container-execution datasets
driven by active learning uncertainty and drift signals.
"""

import json
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
import numpy as np


class AdaptiveDatasetSynthesizer:
    """
    Scientifically generates and curates training/validation datasets with
    adversarial edge cases, active learning reweighting, and distribution shift synthesis.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path(__file__).resolve().parent.parent / "data"
        self.raw_dir = self.output_dir / "raw"
        self.processed_dir = self.output_dir / "processed"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def generate_synthetic_telemetry_batch(
        self,
        n_samples: int = 1500,
        drift_factor: float = 0.0,
        anomaly_ratio: float = 0.08,
        seed: Optional[int] = 42
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """
        Generates feature matrix X and target labels y with controlled distribution drift.
        Features:
          0: cpu_utilization
          1: memory_pressure
          2: io_throughput_normalized
          3: execution_latency_zscore
          4: queue_depth
        """
        if seed is not None:
            np.random.seed(seed)

        # Baseline distributions with drift shifting the centroids
        cpu = np.clip(np.random.normal(0.45 + drift_factor * 0.25, 0.18, size=n_samples), 0.0, 1.0)
        mem = np.clip(np.random.normal(0.50 + drift_factor * 0.20, 0.15, size=n_samples), 0.0, 1.0)
        io = np.clip(np.random.exponential(scale=0.3 + drift_factor * 0.15, size=n_samples), 0.0, 1.0)
        latency = np.random.normal(0.0 + drift_factor * 0.5, 1.0, size=n_samples)
        queue = np.random.poisson(lam=3 + int(drift_factor * 5), size=n_samples) / 15.0

        X = np.stack([cpu, mem, io, latency, queue], axis=1)

        # Target classification: Container Health / Anomaly (0 = Stable, 1 = Degrading/Failure)
        risk_score = 0.3 * cpu + 0.3 * mem + 0.2 * io + 0.2 * np.tanh(latency) + 0.2 * queue
        threshold = np.quantile(risk_score, 1.0 - anomaly_ratio)
        y = (risk_score >= threshold).astype(int)

        metadata = {
            "n_samples": n_samples,
            "feature_dim": 5,
            "feature_names": ["cpu_utilization", "memory_pressure", "io_throughput", "latency_zscore", "queue_depth"],
            "drift_factor": drift_factor,
            "anomaly_ratio": float(np.mean(y)),
            "timestamp": "auto-generated"
        }

        return X, y, metadata

    def save_dataset_split(
        self,
        name: str,
        X: np.ndarray,
        y: np.ndarray,
        metadata: Dict[str, Any]
    ) -> Path:
        """Serializes dataset splits to disk for reproducible experimentation."""
        save_path = self.processed_dir / f"{name}.npz"
        meta_path = self.processed_dir / f"{name}_meta.json"

        np.savez_compressed(save_path, X=X, y=y)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return save_path
