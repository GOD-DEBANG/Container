"""
api/index.py

Vercel ASGI Entrypoint with robust runtime path resolution.
Discovers and exposes the top-level `app` callable for Vercel Serverless.
"""

from __future__ import annotations

import sys
from pathlib import Path

# In Vercel serverless functions, the current file is inside the repository.
# Add all possible candidate roots so dependencies (pulse, vdc, ml) are always resolved.
current_file = Path(__file__).resolve()
server_dir = current_file.parent.parent

candidate_paths = [
    server_dir / "src",     # For 'pulse' package
    server_dir.parent,      # Workspace root for 'vdc', 'ml', 'datasets_hub'
    server_dir,             # Server directory itself
]

for p in candidate_paths:
    str_p = str(p)
    if str_p not in sys.path and p.exists():
        sys.path.insert(0, str_p)

# Import the core ASGI Pulse application
try:
    from pulse.app import app
except Exception as e:
    # Diagnostic fallback for Vercel invocation debugging
    async def app(scope, receive, send):
        if scope["type"] == "http":
            import json
            err_payload = json.dumps({
                "error": True,
                "message": f"Server bootstrap error: {str(e)}",
                "sys_path": sys.path[:5]
            }).encode("utf-8")
            await send({
                "type": "http.response.start",
                "status": 500,
                "headers": [(b"content-type", b"application/json")]
            })
            await send({"type": "http.response.body", "body": err_payload})

__all__ = ["app"]
