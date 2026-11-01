"""
Interactive & Programmatic Dataset Input Handler.
Enables any user (via CLI, script, or programmatic input) to define and request
custom synthetic or container datasets with validation and scientific parameter bounds.
"""

from __future__ import annotations

import uuid
import sys
from pathlib import Path
from typing import Dict, Any, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from datasets_hub.convex_db.schema import DatasetInputSpec, DatasetModality


class DatasetInputHandler:
    """
    Validates, parses, and stages user-provided input parameters for dataset generation.
    """

    @staticmethod
    def create_spec_from_dict(params: Dict[str, Any]) -> DatasetInputSpec:
        """Parses and validates user input dictionary."""
        name = params.get("dataset_name") or f"dataset_{uuid.uuid4().hex[:8]}"
        records = int(params.get("target_records", 500))
        if records <= 0 or records > 1000000:
            raise ValueError(f"target_records must be between 1 and 1,000,000. Got: {records}")

        modality_str = params.get("modality", "numeric_telemetry")
        try:
            modality = DatasetModality(modality_str)
        except ValueError:
            modality = DatasetModality.NUMERIC_TELEMETRY

        drift = float(params.get("drift_factor", 0.0))
        # Auto-normalize drift if user entered percentage (> 1.0)
        if drift > 1.0:
            drift = min(drift / 100.0 if drift <= 100.0 else 1.0, 1.0)
        drift = max(0.0, min(1.0, drift))

        anomaly_in = float(params.get("anomaly_ratio", 0.05))
        # Auto-convert percentage inputs (e.g., 2 -> 0.02, 5 -> 0.05, 8 -> 0.08)
        if anomaly_in > 1.0:
            anomaly_ratio = anomaly_in / 100.0
        else:
            anomaly_ratio = anomaly_in
        anomaly_ratio = max(0.001, min(0.50, anomaly_ratio))

        seed = int(params.get("seed", 42))

        return DatasetInputSpec(
            dataset_name=name,
            target_records=records,
            modality=modality,
            drift_factor=drift,
            anomaly_ratio=anomaly_ratio,
            seed=seed,
            custom_parameters=params.get("custom_parameters", {}),
        )

    @classmethod
    def interactive_cli_prompt(cls) -> DatasetInputSpec:
        """Prompts user interactively in the terminal with smart defaults."""
        print("\n=== Scientific Dataset Generation Input Wizard ===")
        name = input("1. Enter Dataset Name [default: auto-generated]: ").strip()
        if not name:
            name = f"research_run_{uuid.uuid4().hex[:6]}"

        records_in = input("2. Number of Records to Generate [default: 500]: ").strip()
        records = int(records_in) if records_in.isdigit() else 500

        print("3. Available Modalities:")
        print("   [1] numeric_telemetry (CPU, memory, IO, latency distributions)")
        print("   [2] container_execution_trace (Chunk processing and byte throughput)")
        print("   [3] server_event_stream (HTTP request cycles, event pulses)")
        mod_choice = input("   Choose Modality (1-3) [default: 1]: ").strip()
        mod_map = {
            "1": DatasetModality.NUMERIC_TELEMETRY,
            "2": DatasetModality.CONTAINER_EXECUTION_TRACE,
            "3": DatasetModality.SERVER_EVENT_STREAM,
        }
        modality = mod_map.get(mod_choice, DatasetModality.NUMERIC_TELEMETRY)

        drift_in = input("4. Drift Factor (0.0 to 1.0 or % e.g. 8 for 8%) [default: 0.0]: ").strip()
        drift = float(drift_in) if drift_in else 0.0

        anomaly_in = input("5. Anomaly Ratio (e.g. 0.05 or 5 for 5%) [default: 0.05]: ").strip()
        anomaly = float(anomaly_in) if anomaly_in else 0.05

        return cls.create_spec_from_dict({
            "dataset_name": name,
            "target_records": records,
            "modality": modality.value,
            "drift_factor": drift,
            "anomaly_ratio": anomaly,
            "seed": 42,
        })
