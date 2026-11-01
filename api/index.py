"""
api/index.py
============
Vercel Serverless / ASGI entrypoint.
Bootstraps paths and exposes the PULSE ASGI application.
"""

import sys
import traceback
from pathlib import Path

# Ensure Server/src and project root are in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_SRC = REPO_ROOT / "Server" / "src"

for p in (REPO_ROOT, SERVER_SRC):
    if str(p) not in sys.path and p.exists():
        sys.path.insert(0, str(p))

try:
    from pulse.app import app as pulse_app
except Exception as e:
    pulse_app = None
    _init_error = traceback.format_exc()


async def app(scope, receive, send):
    """
    Robust ASGI gateway for Vercel Serverless Function runtime.
    Intercepts and surfaces detailed error diagnostics if internal initialization fails.
    """
    if pulse_app is None:
        err_msg = f"Startup Failed:\n{_init_error}".encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": 500,
            "headers": [
                (b"content-type", b"text/plain; charset=utf-8"),
                (b"content-length", str(len(err_msg)).encode("latin1")),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": err_msg,
            "more_body": False,
        })
        return

    try:
        await pulse_app(scope, receive, send)
    except Exception as exc:
        err_detail = traceback.format_exc().encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": 500,
            "headers": [
                (b"content-type", b"text/plain; charset=utf-8"),
                (b"content-length", str(len(err_detail)).encode("latin1")),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": err_detail,
            "more_body": False,
        })


