"""
api/index.py
============
Vercel Serverless / ASGI entrypoint.
Bootstraps paths and exposes the PULSE ASGI application.
"""

import sys
from pathlib import Path

# Ensure Server/src and project root are in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_SRC = REPO_ROOT / "Server" / "src"

for p in (REPO_ROOT, SERVER_SRC):
    if str(p) not in sys.path and p.exists():
        sys.path.insert(0, str(p))

from pulse.app import app

