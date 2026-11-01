"""
pipelines/system_audit.py
=========================
Runs full diagnostic health probe across Virtual Container, Pulse Server,
and telemetry subsystems, logging results to Convex DB & audit logs.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_SRC = REPO_ROOT / "Server" / "src"

for p in (REPO_ROOT, SERVER_SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from datasets_hub.diagnostics.status_checker import DiagnosticsEngine


def run_audit():
    print("\n" + "=" * 60)
    print("[AUDIT] CONTAINER & SERVER DIAGNOSTIC AUDIT")
    print("=" * 60)
    
    engine = DiagnosticsEngine()
    audit = engine.run_full_system_audit()
    
    print(f"* Container Status:  {audit['container']['status']}")
    print(f"* Server Status:     {audit['server']['status']}")
    print(f"* Audit JSON:        {audit['json_path']}")
    print(f"* Audit CSV:         {audit['csv_path']}")
    print(f"* Convex Sync:       {audit['convex_sync_status']}")
    print("=" * 60 + "\n")
    return audit


if __name__ == "__main__":
    run_audit()
