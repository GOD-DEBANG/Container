"""
Interactive and Scriptable CLI Pipeline for Dataset Generation,
Server/Container Status Audits, and Convex DB Persistence.
"""

from __future__ import annotations

import sys
import argparse
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("DatasetsHubCLI")

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_SRC = REPO_ROOT / "Server" / "src"

for p in (REPO_ROOT, SERVER_SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from datasets_hub.convex_db.schema import DatasetInputSpec, DatasetModality
from datasets_hub.inputs.user_input_handler import DatasetInputHandler
from datasets_hub.outputs.dataset_output_writer import DatasetOutputWriter
from datasets_hub.diagnostics.status_checker import DiagnosticsEngine
from ml.dataset.generator import AdaptiveDatasetSynthesizer


def handle_generate_dataset(args):
    """Generates dataset from user input and stores in JSON and CSV under Convex DB."""
    if args.interactive:
        spec = DatasetInputHandler.interactive_cli_prompt()
    else:
        spec = DatasetInputHandler.create_spec_from_dict({
            "dataset_name": args.name,
            "target_records": args.records,
            "modality": args.modality,
            "drift_factor": args.drift,
            "anomaly_ratio": args.anomaly,
            "seed": args.seed,
        })

    logger.info(f"Generating dataset '{spec.dataset_name}' with {spec.target_records} records...")

    synthesizer = AdaptiveDatasetSynthesizer()
    X, y, meta = synthesizer.generate_synthetic_telemetry_batch(
        n_samples=spec.target_records,
        drift_factor=spec.drift_factor,
        anomaly_ratio=spec.anomaly_ratio,
        seed=spec.seed,
    )

    writer = DatasetOutputWriter()
    result = writer.process_and_persist(
        spec=spec,
        features=X,
        labels=y,
        feature_names=meta.get("feature_names", ["cpu", "mem", "io", "latency", "queue"]),
    )

    logger.info("Dataset successfully generated and committed!")
    logger.info(f"JSON Output Path: {result['json_path']}")
    logger.info(f"CSV Output Path:  {result['csv_path']}")
    logger.info(f"Convex Status:    {result['convex_status']}")
    print("\n--- Sample Preview ---")
    for row in result["sample_preview"]:
        print(row)


def handle_status_audit(args):
    """Runs diagnostics against Container and Server, saving outputs to JSON/CSV in Convex DB."""
    logger.info("Executing deep diagnostic probe on Container and Server...")
    engine = DiagnosticsEngine()
    audit = engine.run_full_system_audit()

    logger.info(f"Virtual Container Status: {audit['container']['status']}")
    logger.info(f"Pulse Server Status:      {audit['server']['status']}")
    logger.info(f"Audit JSON Saved:         {audit['json_path']}")
    logger.info(f"Audit CSV Saved:          {audit['csv_path']}")
    logger.info(f"Convex Sync Status:       {audit['convex_sync_status']}")


def main():
    parser = argparse.ArgumentParser(description="Scientist Dataset Hub & System Diagnostics")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: generate
    p_gen = subparsers.add_parser("generate", help="Create a dataset from user input")
    p_gen.add_argument("--interactive", "-i", action="store_true", help="Launch interactive wizard")
    p_gen.add_argument("--name", "-n", type=str, default="user_custom_dataset", help="Dataset name")
    p_gen.add_argument("--records", "-r", type=int, default=500, help="Number of records")
    p_gen.add_argument("--modality", "-m", type=str, default="numeric_telemetry", help="Modality")
    p_gen.add_argument("--drift", "-d", type=float, default=0.0, help="Drift factor (0.0 to 1.0)")
    p_gen.add_argument("--anomaly", "-a", type=float, default=0.05, help="Anomaly ratio (e.g. 0.05)")
    p_gen.add_argument("--seed", "-s", type=int, default=42, help="RNG seed")
    p_gen.set_defaults(func=handle_generate_dataset)

    # Subcommand: status
    p_stat = subparsers.add_parser("status", help="Run Container & Server diagnostics and log to Convex")
    p_stat.set_defaults(func=handle_status_audit)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
