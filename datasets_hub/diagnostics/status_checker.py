"""
System Health & Status Diagnostics for Server and Container.
Executes probes across Server (ASGI, router, security) and Container (VDC runtime, allocations),
recording outputs in JSON & CSV inside Convex database.
"""

from __future__ import annotations

import sys
import time
import psutil
import csv
from pathlib import Path
from typing import Dict, Any, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SERVER_SRC = REPO_ROOT / "Server" / "src"

for p in (REPO_ROOT, SERVER_SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from datasets_hub.convex_db.database_engine import ConvexDatabaseEngine


class DiagnosticsEngine:
    """
    Performs deep diagnostics and produces formatted status outputs for Container and Server.
    """

    def __init__(self, db_engine: Optional[ConvexDatabaseEngine] = None):
        self.db = db_engine or ConvexDatabaseEngine()

    def check_container_status(self) -> Dict[str, Any]:
        """Runs a live diagnostic probe against the Virtual Container Engine (vdc)."""
        t0 = time.perf_counter()
        probe_result: Dict[str, Any] = {
            "timestamp": time.time(),
            "target": "container_vdc",
            "status": "UNKNOWN",
            "metrics": {},
        }

        try:
            import vdc
            from vdc.container_core.factory import ContainerFactory
            from vdc.models.dataset_model import DatasetSpec
            from vdc.resource_engine.resource_budget import ExecutionPolicy, ResourceBudget

            # Probe container allocation and generation
            spec = DatasetSpec(target_size_bytes=65536, chunk_size_bytes=16384, subchunk_size_bytes=4096)
            budget = ResourceBudget.from_policy(ExecutionPolicy.PERFORMANCE)

            with ContainerFactory.create("diag_probe", spec, budget, REPO_ROOT / "Server" / "data" / "storage") as c:
                report = c.run()

            elapsed = max(1e-6, time.perf_counter() - t0)
            probe_result["status"] = "HEALTHY" if report.success else "DEGRADED"
            probe_result["metrics"] = {
                "container_id": report.container_id,
                "latency_ms": round(elapsed * 1000, 2),
                "throughput_bps": report.metrics.measured_generation_throughput_bytes_per_sec,
                "chunks_processed": report.chunks_processed,
                "cleanup_successful": report.cleanup_successful,
            }
        except Exception as e:
            probe_result["status"] = "OFFLINE"
            probe_result["error"] = str(e)

        return probe_result

    def check_server_status(self) -> Dict[str, Any]:
        """Runs a live diagnostic probe against the Pulse Server subsystems."""
        t0 = time.perf_counter()
        probe_result: Dict[str, Any] = {
            "timestamp": time.time(),
            "target": "server_pulse",
            "status": "UNKNOWN",
            "metrics": {},
        }

        try:
            from pulse.core.router import CompiledRouter
            from pulse.core.pulse import Pulse
            from pulse.fabric.l1_cache import L1Cache

            # Probe router
            router = CompiledRouter()
            router.add_route("GET", "/api/v1/health", lambda: "ok")
            match = router.match("GET", "/api/v1/health")

            # Probe cache
            cache = L1Cache(capacity=100)
            cache.set("probe_key", {"status": "ok"}, ttl_seconds=5.0)
            cache_hit = cache.get("probe_key") is not None

            elapsed = max(1e-6, time.perf_counter() - t0)
            probe_result["status"] = "HEALTHY" if (match and cache_hit) else "DEGRADED"
            probe_result["metrics"] = {
                "router_functional": match is not None,
                "cache_functional": cache_hit,
                "probe_latency_ms": round(elapsed * 1000, 2),
                "host_cpu_percent": psutil.cpu_percent(interval=None),
                "host_memory_used_mb": round(psutil.virtual_memory().used / (1024 * 1024), 2),
            }
        except Exception as e:
            probe_result["status"] = "OFFLINE"
            probe_result["error"] = str(e)

        return probe_result

    def run_full_system_audit(self) -> Dict[str, Any]:
        """
        Executes both checks and persists the audit record in Convex DB (JSON & CSV).
        """
        container_stat = self.check_container_status()
        server_stat = self.check_server_status()

        audit_id = f"audit_{int(time.time())}"
        rows = [
            {
                "subsystem": "VirtualContainer",
                "status": container_stat["status"],
                "latency_ms": container_stat.get("metrics", {}).get("latency_ms", -1),
                "throughput_bps": container_stat.get("metrics", {}).get("throughput_bps", -1),
                "error": container_stat.get("error", "none"),
                "timestamp": container_stat["timestamp"],
            },
            {
                "subsystem": "PulseServer",
                "status": server_stat["status"],
                "latency_ms": server_stat.get("metrics", {}).get("probe_latency_ms", -1),
                "throughput_bps": 0,
                "error": server_stat.get("error", "none"),
                "timestamp": server_stat["timestamp"],
            },
        ]

        commit_result = self.db.persist_dataset_record(
            table_name="system_status_logs",
            record_id=audit_id,
            data_rows=rows,
            metadata={"overall_status": "OPERATIONAL" if (container_stat["status"] == "HEALTHY" and server_stat["status"] == "HEALTHY") else "DEGRADED"},
        )

        # In addition to per-audit records, append to the unified cumulative realtime status CSV report
        cumulative_csv_file = self.db.csv_dir / "system_status_logs" / "realtime_system_status_cumulative.csv"
        file_exists = cumulative_csv_file.exists()
        
        with open(cumulative_csv_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "subsystem", "status", "latency_ms", "throughput_bps", "error"])
            if not file_exists:
                writer.writeheader()
            for r in rows:
                writer.writerow({
                    "timestamp": r["timestamp"],
                    "subsystem": r["subsystem"],
                    "status": r["status"],
                    "latency_ms": r["latency_ms"],
                    "throughput_bps": r["throughput_bps"],
                    "error": r["error"],
                })

        return {
            "audit_id": audit_id,
            "container": container_stat,
            "server": server_stat,
            "json_path": commit_result["json_path"],
            "csv_path": commit_result["csv_path"],
            "cumulative_csv_report": str(cumulative_csv_file),
            "convex_sync_status": commit_result["convex_sync_status"],
        }
