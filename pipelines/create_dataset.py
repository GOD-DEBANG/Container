"""
pipelines/create_dataset.py
===========================
Professional dataset generator controller.
Supports interactive mode, batch preset generation, and CLI overrides,
saving JSON & CSV outputs directly into the Convex data store and reporting status.
"""

from __future__ import annotations

import sys
import argparse
from pathlib import Path

# Path bootstrapping
REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_SRC = REPO_ROOT / "Server" / "src"

for p in (REPO_ROOT, SERVER_SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from datasets_hub.convex_db.schema import DatasetInputSpec
from datasets_hub.inputs.user_input_handler import DatasetInputHandler
from datasets_hub.outputs.dataset_output_writer import DatasetOutputWriter
from ml.dataset.generator import AdaptiveDatasetSynthesizer


def generate(
    name: str = "production_telemetry",
    records: int = 1000,
    modality: str = "numeric_telemetry",
    drift: float = 0.05,
    anomaly: float = 0.05,
    seed: int = 42,
    interactive: bool = False,
):
    print("\n" + "=" * 60)
    print("[PIPELINE] DATASET CREATION CONTROLLER")
    print("=" * 60)

    if interactive:
        spec = DatasetInputHandler.interactive_cli_prompt()
    else:
        spec = DatasetInputHandler.create_spec_from_dict({
            "dataset_name": name,
            "target_records": records,
            "modality": modality,
            "drift_factor": drift,
            "anomaly_ratio": anomaly,
            "seed": seed,
        })

    print(f"\n[CONFIG] Dataset: '{spec.dataset_name}'")
    print(f"[CONFIG] Records: {spec.target_records} | Modality: {spec.modality.value}")
    print(f"[CONFIG] Drift Factor: {spec.drift_factor} | Anomaly Ratio: {spec.anomaly_ratio} | Seed: {spec.seed}")
    print("\n[SYNTHESIZING] Generating synthetic distribution batches...")

    synthesizer = AdaptiveDatasetSynthesizer()
    X, y, meta = synthesizer.generate_by_modality(
        modality=spec.modality.value,
        n_samples=spec.target_records,
        drift_factor=spec.drift_factor,
        anomaly_ratio=spec.anomaly_ratio,
        seed=spec.seed,
    )

    print(f"[PERSISTING] Writing and committing into Convex DB & local storage...")
    writer = DatasetOutputWriter()
    result = writer.process_and_persist(
        spec=spec,
        features=X,
        labels=y,
        feature_names=meta.get("feature_names", []),
    )

    print("\n" + "=" * 20 + " SUCCESS " + "=" * 20)
    print(f"* JSON Dataset:  {result['json_path']}")
    print(f"* CSV Dataset:   {result['csv_path']}")
    print(f"* Convex Sync:   {result['convex_status']}")
    print(f"* Records Saved: {spec.target_records}")
    print(f"* Features:      {', '.join(meta.get('feature_names', []))}")
    print("-" * 60)
    print("Statistical Summary:")
    for f_name, f_stats in meta.get("feature_statistics", {}).items():
        print(f"  {f_name:24s} -> mean: {f_stats['mean']:8.3f} | std: {f_stats['std']:8.3f}")
    print("-" * 60)
    print("Preview of generated rows:")
    for i, row in enumerate(result["sample_preview"][:5]):
        print(f"  [{i+1}] {row}")
    print("=" * 60 + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description="Dataset Creation Pipeline Controller")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run interactive prompt wizard")
    parser.add_argument("--name", "-n", type=str, default="synthetic_telemetry_v1", help="Dataset name")
    parser.add_argument("--records", "-r", type=int, default=1000, help="Number of records to generate")
    parser.add_argument("--modality", "-m", type=str, default="numeric_telemetry", help="Data modality")
    parser.add_argument("--drift", "-d", type=float, default=0.05, help="Drift coefficient (0.0 to 1.0)")
    parser.add_argument("--anomaly", "-a", type=float, default=0.05, help="Anomaly fraction (0.0 to 1.0)")
    parser.add_argument("--seed", "-s", type=int, default=42, help="Random seed")

    args = parser.parse_args()
    generate(
        name=args.name,
        records=args.records,
        modality=args.modality,
        drift=args.drift,
        anomaly=args.anomaly,
        seed=args.seed,
        interactive=args.interactive,
    )


if __name__ == "__main__":
    main()
