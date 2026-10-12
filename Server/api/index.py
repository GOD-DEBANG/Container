"""
api/index.py

Thin Vercel ASGI Entrypoint.
Exposes top-level `app` callable adhering to Vercel Python runtime discovery.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is on sys.path in Vercel serverless environment
src_dir = str(Path(__file__).resolve().parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from pulse.app import app  # noqa: E402

__all__ = ["app"]
