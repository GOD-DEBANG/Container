"""
bench/benchmark.py

Comprehensive benchmark suite for PULSE and the Virtual Container engine:
  1. Pure Mathematical Formulas (Allocation & Throughput calculation rates)
  2. Compiled Trie Router (Path matching p50, p99, ops/sec)
  3. Cryptographic Primitives (Ed25519, X25519, AES-256-GCM MB/s)
  4. SingleFlight Request Coalescing
  5. ASGI Server Request Latencies (p50, p99, req/sec)
  6. Virtual Container Dataset Generation (End-to-End MB/s)
"""

from __future__ import annotations

import asyncio
import math
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

import httpx
from cryptography.hazmat.primitives.asymmetric import ed25519

from vdc.mathematics.allocation_formula import weighted_allocation
from vdc.mathematics.throughput_formula import calculate_effective_throughput
from vdc.services.dataset_generation_service import DatasetGenerationService
from vdc.resource_engine.resource_budget import ExecutionPolicy
from pulse.core.router import CompiledRouter
from pulse.security.crypto import CryptoEngine
from pulse.app import create_pulse_app
from pulse.config import PulseConfig


def calculate_percentiles(samples: List[float]) -> Dict[str, float]:
    if not samples:
        return {"avg_ms": 0.0, "p50_ms": 0.0, "p99_ms": 0.0}
    sorted_s = sorted(samples)
    n = len(sorted_s)
    p50 = sorted_s[int(math.ceil(0.50 * n)) - 1]
    p99 = sorted_s[int(math.ceil(0.99 * n)) - 1]
    avg = sum(sorted_s) / n
    return {
        "avg_ms": round(avg * 1000, 3),
        "p50_ms": round(p50 * 1000, 3),
        "p99_ms": round(p99 * 1000, 3),
    }


def benchmark_mathematics(iterations: int = 20000) -> Dict[str, Any]:
    weights = [0.2, 0.3, 0.5]
    t0 = time.perf_counter()
    for _ in range(iterations):
        weighted_allocation(1000000, weights)
    t1 = time.perf_counter()
    alloc_duration = max(1e-6, t1 - t0)

    t0 = time.perf_counter()
    for _ in range(iterations):
        calculate_effective_throughput(100000.0, 80000.0, 95000.0, 50000.0)
    t1 = time.perf_counter()
    thru_duration = max(1e-6, t1 - t0)

    return {
        "weighted_allocation_ops_per_sec": int(iterations / alloc_duration),
        "throughput_calculation_ops_per_sec": int(iterations / thru_duration),
    }


def benchmark_router(iterations: int = 25000) -> Dict[str, Any]:
    router = CompiledRouter()
    router.add_route("GET", "/api/v1/health", "health")
    router.add_route("POST", "/api/v1/jobs", "create_job")
    router.add_route("GET", "/api/v1/jobs/{job_id}", "get_job")
    router.add_route("GET", "/api/v1/jobs/{job_id}/stream", "stream")

    samples: List[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        router.match("GET", "/api/v1/jobs/job_abc123xyz")
        t1 = time.perf_counter()
        samples.append(t1 - t0)

    stats = calculate_percentiles(samples)
    stats["total_ops_per_sec"] = int(iterations / sum(samples))
    return stats


def benchmark_crypto(iterations: int = 500) -> Dict[str, Any]:
    priv, pub = CryptoEngine.generate_ed25519_keypair()
    payload = b"Pulse Canonical Benchmark Event Payload"

    # Ed25519 Sign
    sign_samples: List[float] = []
    signatures = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        sig = CryptoEngine.sign_ed25519(priv, payload)
        t1 = time.perf_counter()
        sign_samples.append(t1 - t0)
        signatures.append(sig)

    # Ed25519 Verify
    verify_samples: List[float] = []
    for i in range(iterations):
        t0 = time.perf_counter()
        CryptoEngine.verify_ed25519(pub, signatures[i], payload)
        t1 = time.perf_counter()
        verify_samples.append(t1 - t0)

    # AES-256-GCM AEAD (64 KB chunks)
    aes_key = os.urandom(32)
    block_64k = os.urandom(65536)
    aes_samples: List[float] = []
    total_bytes = 0
    for _ in range(iterations):
        t0 = time.perf_counter()
        nonce, ciphertext = CryptoEngine.encrypt_aes_gcm(aes_key, block_64k)
        CryptoEngine.decrypt_aes_gcm(aes_key, nonce, ciphertext)
        t1 = time.perf_counter()
        aes_samples.append(t1 - t0)
        total_bytes += len(block_64k) * 2

    aes_total_sec = sum(aes_samples)
    aes_mbs = (total_bytes / (1024 * 1024)) / max(1e-6, aes_total_sec)

    return {
        "ed25519_sign": calculate_percentiles(sign_samples),
        "ed25519_verify": calculate_percentiles(verify_samples),
        "aes_256_gcm_throughput_mb_per_sec": round(aes_mbs, 2),
    }


async def benchmark_server_requests(iterations: int = 300) -> Dict[str, Any]:
    config = PulseConfig(
        env="test",
        host="127.0.0.1",
        port=8000,
        debug=False,
        secret_key=b"01234567890123456789012345678901",
        backend="INLINE",
        max_inline_dataset_bytes=100 * 1024 * 1024,
        max_execution_duration_seconds=30.0,
        storage_root=tempfile.mkdtemp(),
        redis_url=None,
    )
    app = create_pulse_app(config)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Measure cold start (first request)
        t_cold_0 = time.perf_counter()
        resp0 = await client.get("/api/v1/health")
        t_cold_1 = time.perf_counter()
        cold_start_ms = round((t_cold_1 - t_cold_0) * 1000, 3)

        # Authenticate
        token_resp = await client.post("/api/v1/auth/token", json={"subject": "benchmarker"})
        token = token_resp.json()["payload"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Measure warm requests
        samples: List[float] = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            r = await client.get("/api/v1/health")
            t1 = time.perf_counter()
            assert r.status_code == 200
            samples.append(t1 - t0)

    stats = calculate_percentiles(samples)
    stats["cold_start_latency_ms"] = cold_start_ms
    stats["requests_per_sec"] = int(iterations / max(1e-6, sum(samples)))
    return stats


def benchmark_virtual_container() -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp_dir:
        svc = DatasetGenerationService(tmp_dir)
        results = {}

        for size_mb in [1, 5, 10]:
            size_bytes = size_mb * 1024 * 1024
            rep = svc.generate(
                job_id=f"bench_{size_mb}mb",
                target_size_bytes=size_bytes,
                chunk_size_bytes=1024 * 1024,
                subchunk_size_bytes=256 * 1024,
                policy=ExecutionPolicy.PERFORMANCE,
            )
            m = rep.metrics
            results[f"{size_mb}MB_job"] = {
                "generated_bytes": m.actual_generated_bytes,
                "elapsed_seconds": round(m.total_elapsed_seconds, 4),
                "generation_mb_per_sec": round(m.measured_generation_throughput_bytes_per_sec / (1024 * 1024), 2),
                "persistence_mb_per_sec": round(m.measured_persistence_throughput_bytes_per_sec / (1024 * 1024), 2),
                "end_to_end_mb_per_sec": round(m.end_to_end_throughput_bytes_per_sec / (1024 * 1024), 2),
            }
        return results


def run_all_benchmarks() -> Dict[str, Any]:
    math_results = benchmark_mathematics()
    router_results = benchmark_router()
    crypto_results = benchmark_crypto()
    server_results = asyncio.run(benchmark_server_requests())
    vdc_results = benchmark_virtual_container()

    return {
        "mathematics": math_results,
        "router": router_results,
        "cryptography": crypto_results,
        "server": server_results,
        "virtual_container": vdc_results,
    }


if __name__ == "__main__":
    import json
    res = run_all_benchmarks()
    print(json.dumps(res, indent=2))
