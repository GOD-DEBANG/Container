"""
tests/integration/test_e2e_server.py

End-to-End integration test suite for PULSE Server.
Tests full ASGI HTTP lifecycle:
  - Auth token issuance
  - Ed25519 cryptographic signing
  - Replay protection nonce submission
  - Inline dataset generation inside Virtual Container
  - Status retrieval
  - SSE progress streaming
  - Verified dataset download
"""

import base64
import hashlib
import json
import uuid
import pytest
import httpx
from cryptography.hazmat.primitives.asymmetric import ed25519

from pulse.app import create_pulse_app
from pulse.config import PulseConfig


@pytest.mark.asyncio
async def test_e2e_pulse_server_workflow(tmp_path):
    # Configure test server
    config = PulseConfig(
        env="test",
        host="127.0.0.1",
        port=8000,
        debug=True,
        secret_key=b"01234567890123456789012345678901",
        backend="INLINE",
        max_inline_dataset_bytes=10 * 1024 * 1024,
        max_execution_duration_seconds=30.0,
        storage_root=str(tmp_path / "storage"),
        redis_url=None,
    )
    app = create_pulse_app(config)

    # In-memory ASGI transport with httpx
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Health check
        health_resp = await client.get("/api/v1/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["payload"]["status"] == "healthy"

        # 2. Authenticate
        token_resp = await client.post(
            "/api/v1/auth/token",
            json={"subject": "test_e2e_user", "ttl_seconds": 600},
        )
        assert token_resp.status_code == 200
        token = token_resp.json()["payload"]["access_token"]
        assert token is not None

        # 3. Submit Dataset Job with Ed25519 signature
        client_priv = ed25519.Ed25519PrivateKey.generate()
        client_pub = client_priv.public_key()
        client_pub_b64 = base64.b64encode(client_pub.public_bytes_raw()).decode("ascii")

        job_payload = {
            "target_size_bytes": 100000, # 100 KB
            "chunk_size_bytes": 25000,   # 25 KB
            "subchunk_size_bytes": 5000, # 5 KB
            "policy": "PERFORMANCE",
            "backend": "INLINE",
            "seed": 999,
        }

        canonical_bytes = json.dumps(job_payload, sort_keys=True).encode("utf-8")
        signature_b64 = base64.b64encode(client_priv.sign(canonical_bytes)).decode("ascii")
        nonce = f"nonce_{uuid.uuid4().hex}"

        headers = {
            "Authorization": f"Bearer {token}",
            "X-Pulse-Signature": signature_b64,
            "X-Pulse-Public-Key": client_pub_b64,
            "X-Pulse-Nonce": nonce,
        }

        submit_resp = await client.post("/api/v1/jobs", json=job_payload, headers=headers)
        assert submit_resp.status_code == 200
        submit_data = submit_resp.json()["payload"]
        job_id = submit_data["job_id"]
        assert job_id is not None
        assert submit_data["status"] == "COMPLETED"

        # 4. Query Job Status
        status_resp = await client.get(f"/api/v1/jobs/{job_id}")
        assert status_resp.status_code == 200
        status_data = status_resp.json()["payload"]
        assert status_data["status"] == "COMPLETED"
        assert status_data["metrics"]["actual_generated_bytes"] == 100000
        checksum_expected = status_data["checksum_sha256"]

        # 5. Stream SSE Events
        stream_resp = await client.get(f"/api/v1/jobs/{job_id}/stream")
        assert stream_resp.status_code == 200
        assert "text/event-stream" in stream_resp.headers["content-type"]
        assert "pulse_completed" in stream_resp.text

        # 6. Download Dataset and verify SHA-256
        download_resp = await client.get(f"/api/v1/jobs/{job_id}/download")
        assert download_resp.status_code == 200
        data = download_resp.content
        assert len(data) == 100000
        actual_sha = hashlib.sha256(data).hexdigest()
        assert actual_sha == checksum_expected
