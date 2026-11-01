"""
pipelines/train_model.py
========================
Model training controller for PULSE / VDC Adaptive Classifier.
Loads synthesized or real datasets from the Convex data store, applies normalization,
trains the neural model with convergence monitoring, and saves weight checkpoints.
"""

from __future__ import annotations

import sys
import json
import argparse
from pathlib import Path
from typing import Tuple, Dict, Any
import numpy as np

# Path bootstrapping
REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_SRC = REPO_ROOT / "Server" / "src"

for p in (REPO_ROOT, SERVER_SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from datasets_hub.convex_db.database_engine import ConvexDatabaseEngine
from ml.models.adaptive_classifier import AdaptiveClassifier
from ml.training.trainer import SelfEvolvingTrainer


def load_dataset(dataset_name: str) -> Tuple[np.ndarray, np.ndarray, list[str]]:
    """Loads dataset from convex data store in json or csv."""
    engine = ConvexDatabaseEngine()
    record = engine.load_record_json("synthesized_datasets", dataset_name)
    
    if not record or "data" not in record or not record["data"]:
        raise ValueError(f"Dataset '{dataset_name}' not found or empty in datasets_hub/data_store/convex_records/json/synthesized_datasets/")

    rows = record["data"]
    feature_names = record.get("metadata", {}).get("feature_names", [])

    if not feature_names:
        # Infer features excluding meta columns
        sample = rows[0]
        exclude = {"sample_index", "timestamp_ms", "target_label", "is_anomaly", "record_id"}
        feature_names = [k for k in sample.keys() if k not in exclude]

    X = np.array([[float(r[col]) for col in feature_names] for r in rows], dtype=np.float32)
    y = np.array([int(r.get("target_label", 0)) for r in rows], dtype=np.int64)

    return X, y, feature_names


def train(
    dataset_name: str = "telemetry_production_v1",
    epochs: int = 30,
    batch_size: int = 32,
    lr: float = 0.05,
    hidden_dim: int = 16,
    val_split: float = 0.2,
    save_path: str | None = None,
) -> Dict[str, Any]:
    print("\n" + "=" * 60)
    print("[PIPELINE] ADAPTIVE MODEL TRAINING CONTROLLER")
    print("=" * 60)
    print(f"Loading dataset: '{dataset_name}'...")
    X, y, feature_names = load_dataset(dataset_name)

    n_samples = len(X)
    print(f"Loaded {n_samples} samples with {len(feature_names)} features: {', '.join(feature_names)}")

    # Split train/validation
    np.random.seed(42)
    indices = np.random.permutation(n_samples)
    val_count = int(n_samples * val_split)
    train_idx, val_idx = indices[val_count:], indices[:val_count]

    X_train, y_train = X[train_idx], y[train_idx]
    X_val, y_val = X[val_idx], y[val_idx]

    # Standardize features
    mean = np.mean(X_train, axis=0, keepdims=True)
    std = np.std(X_train, axis=0, keepdims=True) + 1e-8

    X_train_norm = (X_train - mean) / std
    X_val_norm = (X_val - mean) / std

    # Instantiate model & trainer
    model = AdaptiveClassifier(
        input_dim=len(feature_names),
        hidden_dim=hidden_dim,
        output_dim=len(np.unique(y)),
    )
    trainer = SelfEvolvingTrainer(model=model, learning_rate=lr)

    print(f"Beginning training across {epochs} epochs (Batch size: {batch_size}, LR: {lr})...\n")

    history = []
    for epoch in range(1, epochs + 1):
        train_metrics = trainer.train_epoch(X_train_norm, y_train, batch_size=batch_size)
        val_metrics = trainer.evaluate(X_val_norm, y_val)
        history.append({
            "epoch": epoch,
            "loss": train_metrics["loss"],
            "accuracy": train_metrics["accuracy"],
            "val_loss": val_metrics["val_loss"],
            "val_accuracy": val_metrics["val_accuracy"],
        })
        if epoch % 5 == 0 or epoch == 1 or epoch == epochs:
            print(f"Epoch {epoch:3d}/{epochs} | Loss: {train_metrics['loss']:.4f} | Acc: {train_metrics['accuracy']*100:.1f}% | Val Loss: {val_metrics['val_loss']:.4f} | Val Acc: {val_metrics['val_accuracy']*100:.1f}%")

    # Save artifacts
    artifacts_dir = REPO_ROOT / "ml" / "artifacts"
    weights_path = Path(save_path) if save_path else artifacts_dir / f"{dataset_name}_model_weights.npz"
    model.save(weights_path)

    # Save scaler and metrics
    scaler_path = artifacts_dir / f"{dataset_name}_scaler.json"
    scaler_payload = {
        "feature_names": feature_names,
        "mean": mean.flatten().tolist(),
        "std": std.flatten().tolist(),
    }
    with open(scaler_path, "w", encoding="utf-8") as f:
        json.dump(scaler_payload, f, indent=2)

    history_path = artifacts_dir / "metrics" / f"{dataset_name}_training_history.json"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    print("\n" + "=" * 20 + " TRAINING COMPLETE " + "=" * 20)
    print(f"* Weights Saved: {weights_path}")
    print(f"* Scaler Saved:  {scaler_path}")
    print(f"* Metrics Log:   {history_path}")
    print(f"* Final Accuracy: {val_metrics['val_accuracy']*100:.2f}% (Val Loss: {val_metrics['val_loss']:.4f})")
    print("=" * 60 + "\n")

    return {
        "model": model,
        "weights_path": str(weights_path),
        "scaler_path": str(scaler_path),
        "final_accuracy": val_metrics["val_accuracy"],
        "final_val_loss": val_metrics["val_loss"],
    }


def main():
    parser = argparse.ArgumentParser(description="PULSE ML Training Controller")
    parser.add_argument("--dataset", "-d", type=str, default="telemetry_production_v1", help="Dataset name in convex records")
    parser.add_argument("--epochs", "-e", type=int, default=30, help="Number of training epochs")
    parser.add_argument("--batch-size", "-b", type=int, default=32, help="Mini-batch size")
    parser.add_argument("--lr", type=float, default=0.05, help="Learning rate")
    parser.add_argument("--hidden-dim", type=int, default=16, help="Hidden dimension")
    parser.add_argument("--output", "-o", type=str, default=None, help="Custom weights save path")

    args = parser.parse_args()
    train(
        dataset_name=args.dataset,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        hidden_dim=args.hidden_dim,
        save_path=args.output,
    )


if __name__ == "__main__":
    main()

