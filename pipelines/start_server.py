"""
pipelines/start_server.py
=========================
Professional, cross-platform launcher for the PULSE ASGI Server.
Automatically binds virtual environments, loads environment variables,
and launches Uvicorn with auto-reload and robust path resolution.
"""

from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_DIR = REPO_ROOT / "Server"
SERVER_SRC = SERVER_DIR / "src"
VENV_PYTHON = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
if not VENV_PYTHON.exists():
    VENV_PYTHON = Path(sys.executable)

def ensure_env_file():
    """Ensures .env exists in Server/ from .env.example if missing."""
    env_file = SERVER_DIR / ".env"
    example_file = SERVER_DIR / ".env.example"
    if not env_file.exists() and example_file.exists():
        print("[SETUP] Creating Server/.env from .env.example...")
        env_file.write_text(example_file.read_text(encoding="utf-8"), encoding="utf-8")

def run():
    ensure_env_file()
    
    # Configure PYTHONPATH to include Server/src and REPO_ROOT
    env = os.environ.copy()
    current_pp = env.get("PYTHONPATH", "")
    additional_paths = [str(SERVER_SRC), str(REPO_ROOT), str(SERVER_DIR)]
    env["PYTHONPATH"] = os.pathsep.join(additional_paths + ([current_pp] if current_pp else []))
    
    cmd = [
        str(VENV_PYTHON),
        "-m", "uvicorn",
        "pulse.app:app",
        "--host", "127.0.0.1",
        "--port", "8000",
        "--reload"
    ]
    
    print("\n" + "=" * 60)
    print("[RUNNING] STARTING PULSE ASGI SERVER")
    print(f"* Root URL:   http://127.0.0.1:8000")
    print(f"* Health API: http://127.0.0.1:8000/api/v1/health")
    print(f"* Python:     {VENV_PYTHON}")
    print(f"* Directory:  {SERVER_DIR}")
    print("=" * 60 + "\n")
    
    try:
        subprocess.run(cmd, cwd=str(SERVER_DIR), env=env, check=True)
    except KeyboardInterrupt:
        print("\n[STOP] Server stopped by user.")
    except Exception as exc:
        print(f"\n[ERROR] Failed to start server: {exc}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run()
