"""
Convex Database Client & Local Storage Engine.
Stores dataset outputs, schemas, container diagnostics, and telemetry
in JSON, CSV, and directly syncs to Convex cloud when configured.
"""

from __future__ import annotations

import os
import json
import csv
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx

logger = logging.getLogger("ConvexStorageEngine")


class ConvexDatabaseEngine:
    """
    Manages dual-persistence of datasets and system telemetry:
    1. Local filesystem persistence (JSON + CSV format).
    2. Cloud persistence to Convex backend if CONVEX_URL is configured.
    """

    def __init__(self, db_root: Optional[Path | str] = None, convex_url: Optional[str] = None):
        # Auto-load CONVEX_URL from .env if not already set
        if not convex_url and not os.getenv("CONVEX_URL"):
            env_file = Path(__file__).resolve().parent.parent.parent / ".env"
            if env_file.exists():
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    if line.startswith("CONVEX_URL="):
                        os.environ["CONVEX_URL"] = line.split("=", 1)[1].strip()
                        break

        self.convex_url = convex_url or os.getenv("CONVEX_URL", "https://adventurous-kudu-539.convex.cloud")
        self.db_root = Path(db_root or Path(__file__).resolve().parent.parent / "data_store" / "convex_records")
        self.json_dir = self.db_root / "json"
        self.csv_dir = self.db_root / "csv"
        
        self.json_dir.mkdir(parents=True, exist_ok=True)
        self.csv_dir.mkdir(parents=True, exist_ok=True)

    def persist_dataset_record(
        self,
        table_name: str,
        record_id: str,
        data_rows: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        Saves dataset records in both JSON and CSV formats, and pushes to Convex.
        """
        table_json_dir = self.json_dir / table_name
        table_csv_dir = self.csv_dir / table_name
        table_json_dir.mkdir(parents=True, exist_ok=True)
        table_csv_dir.mkdir(parents=True, exist_ok=True)

        json_file = table_json_dir / f"{record_id}.json"
        csv_file = table_csv_dir / f"{record_id}.csv"

        payload = {
            "record_id": record_id,
            "table": table_name,
            "metadata": metadata or {},
            "total_records": len(data_rows),
            "data": data_rows,
        }

        # 1. Save JSON
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        # 2. Save CSV
        if data_rows:
            keys = list(data_rows[0].keys())
            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                for row in data_rows:
                    writer.writerow({k: row.get(k, "") for k in keys})
        else:
            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                f.write("record_id,status\n")

        # 3. Synchronize with Convex Cloud in real-time
        sync_status = "saved_locally"
        if self.convex_url:
            try:
                endpoint = f"{self.convex_url.rstrip('/')}/api/mutation"
                if table_name == "synthesized_datasets":
                    mutation_payload = {
                        "path": "mutations:insertDatasetBatch",
                        "args": {
                            "record_id": record_id,
                            "dataset_name": record_id,
                            "rows": data_rows[:250],
                            "metadata": metadata or {},
                        },
                    }
                else:
                    # system_status_logs
                    first_row = data_rows[0] if data_rows else {}
                    mutation_payload = {
                        "path": "mutations:logSystemStatus",
                        "args": {
                            "record_id": record_id,
                            "subsystem": first_row.get("subsystem", "System"),
                            "status": first_row.get("status", "HEALTHY"),
                            "latency_ms": float(first_row.get("latency_ms", 0.0)),
                            "throughput_bps": float(first_row.get("throughput_bps", 0.0)),
                            "error": str(first_row.get("error", "none")),
                            "timestamp": float(first_row.get("timestamp", 0.0)),
                            "metadata": metadata or {},
                        },
                    }

                resp = httpx.post(endpoint, json=mutation_payload, timeout=8.0)
                if resp.status_code == 200:
                    sync_status = "synced_to_convex_cloud"
                    logger.info(f"⚡ [Convex Realtime Auto-Sync] Pushed {record_id} to {table_name}")
                else:
                    sync_status = f"convex_http_status_{resp.status_code}"
            except Exception as e:
                logger.warning(f"Convex auto-sync fallback: {e}")
                sync_status = "convex_cloud_deferred"

        return {
            "json_path": str(json_file),
            "csv_path": str(csv_file),
            "convex_sync_status": sync_status,
        }

    def list_records(self, table_name: str) -> List[str]:
        """Lists record IDs stored in the Convex database table."""
        table_json_dir = self.json_dir / table_name
        if not table_json_dir.exists():
            return []
        return [f.stem for f in table_json_dir.glob("*.json")]

    def load_record_json(self, table_name: str, record_id: str) -> Optional[Dict[str, Any]]:
        """Loads a record by ID in JSON format."""
        file_path = self.json_dir / table_name / f"{record_id}.json"
        if not file_path.exists():
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
