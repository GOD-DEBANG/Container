"""
Dataset Output Manager & Dual Format Formatter.
Serializes generated datasets into clean JSON and CSV representations,
records metadata, and commits directly into the Convex database.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from datasets_hub.convex_db.database_engine import ConvexDatabaseEngine
from datasets_hub.convex_db.schema import DatasetInputSpec


class DatasetOutputWriter:
    """
    Transforms in-memory dataset tensors and records into standard schemas,
    writes both JSON and CSV files, and persists them into the Convex store.
    """

    def __init__(self, db_engine: Optional[ConvexDatabaseEngine] = None):
        self.db = db_engine or ConvexDatabaseEngine()

    def process_and_persist(
        self,
        spec: DatasetInputSpec,
        features: np.ndarray,
        labels: np.ndarray,
        feature_names: List[str],
        additional_telemetry: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Converts array data into structured dictionary rows, persists in Convex,
        and outputs both JSON and CSV files.
        """
        rows: List[Dict[str, Any]] = []
        n_samples = features.shape[0]

        for i in range(n_samples):
            row_dict = {
                "sample_index": i,
                "timestamp_ms": i * 10,
            }
            # Append features
            for f_idx, f_name in enumerate(feature_names):
                row_dict[f_name] = round(float(features[i, f_idx]), 5)

            # Target label
            row_dict["target_label"] = int(labels[i])
            row_dict["is_anomaly"] = bool(labels[i] == 1)

            # Include real container telemetry if provided
            if additional_telemetry and i < len(additional_telemetry):
                for k, v in additional_telemetry[i].items():
                    row_dict[f"container_{k}"] = v

            rows.append(row_dict)

        meta = {
            "dataset_name": spec.dataset_name,
            "modality": spec.modality.value,
            "sample_count": n_samples,
            "drift_factor": spec.drift_factor,
            "anomaly_ratio": spec.anomaly_ratio,
            "feature_dim": len(feature_names),
            "feature_names": feature_names,
        }

        # Commit to Convex DB
        commit_result = self.db.persist_dataset_record(
            table_name="synthesized_datasets",
            record_id=spec.dataset_name,
            data_rows=rows,
            metadata=meta,
        )

        return {
            "dataset_name": spec.dataset_name,
            "total_records": n_samples,
            "json_path": commit_result["json_path"],
            "csv_path": commit_result["csv_path"],
            "convex_status": commit_result["convex_sync_status"],
            "sample_preview": rows[:3],
        }
