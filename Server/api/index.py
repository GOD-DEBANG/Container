"""
api/index.py

Thin Vercel ASGI Entrypoint.
Exposes top-level `app` callable adhering to Vercel Python runtime discovery.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure both Server/src and top-level workspace root (for vdc and ml) are on sys.path
server_dir = Path(__file__).resolve().parent.parent
src_dir = str(server_dir / "src")
repo_root = str(server_dir.parent)

for p in (src_dir, repo_root):
    if p not in sys.path:
        sys.path.insert(0, p)

from pulse.app import app  # noqa: E402

__all__ = ["app"]
