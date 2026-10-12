"""
clients/python_client.py

PULSE Python SDK Client.
Supports:
  - Token authentication
  - Ed25519 cryptographic request signing
  - Replay-protected job submission
  - Server-Sent Events (SSE) progress streaming with auto-reconnect cursors
  - Direct dataset verification and download
"""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from typing import Any, AsyncIterator, Dict, Optional

import httpx
from cryptography.hazmat.primitives.asymmetric import ed25519


class PulseClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        private_key: Optional[ed25519.Ed25519PrivateKey] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.private_key = private_key or ed25519.Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self.public_key_b64 = base64.b64encode(self.public_key.public_bytes_raw()).decode("ascii")
        self.token: Optional[str] = None
        self._http = httpx.AsyncClient(base_url=self.base_url, timeout=60.0)

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> PulseClient:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def authenticate(self, subject: str = "python_client", ttl_seconds: int = 3600) -> str:
        """Obtain short-lived bearer token."""
        resp = await self._http.post(
            "/api/v1/auth/token",
            json={"subject": subject, "ttl_seconds": ttl_seconds},
        )
        resp.raise_for_status()
        data = resp.json()["payload"]
        self.token = data["access_token"]
        return self.token

    def _sign_payload(self, payload: Dict[str, Any]) -> str:
        canonical_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        sig = self.private_key.sign(canonical_bytes)
        return base64.b64encode(sig).decode("ascii")

    async def submit_job(
        self,
        target_size_bytes: int,
        chunk_size_bytes: int = 1048576,
        subchunk_size_bytes: int = 262144,
        policy: str = "BALANCED",
        backend: str = "INLINE",
        seed: int = 42,
    ) -> Dict[str, Any]:
        """Submit a dataset generation job."""
        if not self.token:
            await self.authenticate()

        payload = {
            "target_size_bytes": target_size_bytes,
            "chunk_size_bytes": chunk_size_bytes,
            "subchunk_size_bytes": subchunk_size_bytes,
            "policy": policy,
            "backend": backend,
            "seed": seed,
        }

        nonce = f"nonce_{uuid.uuid4().hex}"
        signature = self._sign_payload(payload)

        headers = {
            "Authorization": f"Bearer {self.token}",
            "X-Pulse-Signature": signature,
            "X-Pulse-Public-Key": self.public_key_b64,
            "X-Pulse-Nonce": nonce,
            "Content-Type": "application/json",
        }

        resp = await self._http.post("/api/v1/jobs", json=payload, headers=headers)
        if resp.status_code >= 400:
            raise RuntimeError(f"Job submission failed ({resp.status_code}): {resp.text}")

        return resp.json()["payload"]

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Query current job status."""
        resp = await self._http.get(f"/api/v1/jobs/{job_id}")
        resp.raise_for_status()
        return resp.json()["payload"]

    async def stream_progress(self, job_id: str) -> AsyncIterator[Dict[str, Any]]:
        """Stream progress events via Server-Sent Events."""
        _last_id = 0
        async with self._http.stream("GET", f"/api/v1/jobs/{job_id}/stream") as response:
            async for line in response.aiter_lines():
                if not line:
                    continue
                if line.startswith("id:"):
                    try:
                        _last_id = int(line[3:].strip())
                    except ValueError:
                        pass
                elif line.startswith("data:"):
                    data_str = line[5:].strip()
                    try:
                        parsed = json.loads(data_str)
                        yield parsed
                        if parsed.get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
                            return
                    except Exception:
                        pass

    async def download_dataset(self, job_id: str) -> bytes:
        """Download dataset and verify SHA-256 integrity."""
        # 1. Fetch metadata
        meta_resp = await self._http.get(f"/api/v1/jobs/{job_id}")
        meta_resp.raise_for_status()
        job_meta = meta_resp.json()["payload"]
        expected_sha = job_meta.get("checksum_sha256")

        # 2. Download binary bytes
        resp = await self._http.get(f"/api/v1/jobs/{job_id}/download")
        resp.raise_for_status()
        data = resp.content

        # 3. Verify Checksum
        if expected_sha:
            actual_sha = hashlib.sha256(data).hexdigest()
            if actual_sha != expected_sha:
                raise ValueError(f"Downloaded dataset SHA-256 mismatch! Got {actual_sha}, expected {expected_sha}")

        return data
