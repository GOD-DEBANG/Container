"""
scripts/run_benchmarks.py

Executable benchmark runner script.
Prints formatted benchmark results.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is on sys.path (bench, pulse, vdc all live under src/)
src_dir = str(Path(__file__).resolve().parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from bench.benchmark import run_all_benchmarks


def main() -> None:
    print("=" * 70)
    print("  RUNNING PULSE & VIRTUAL CONTAINER BENCHMARK SUITE")
    print("=" * 70)
    results = run_all_benchmarks()

    print("\n[1] Pure Computational Mathematics Engine:")
    m = results["mathematics"]
    print(f"  - Weighted Allocation       : {m['weighted_allocation_ops_per_sec']:,} ops/sec")
    print(f"  - Throughput Min Equation   : {m['throughput_calculation_ops_per_sec']:,} ops/sec")

    print("\n[2] Compiled Trie Router:")
    r = results["router"]
    print(f"  - p50 Latency               : {r['p50_ms']} ms")
    print(f"  - p99 Latency               : {r['p99_ms']} ms")
    print(f"  - Throughput                : {r['total_ops_per_sec']:,} matches/sec")

    print("\n[3] Cryptographic Primitives:")
    c = results["cryptography"]
    print(f"  - Ed25519 Sign (p50 / p99)  : {c['ed25519_sign']['p50_ms']} ms / {c['ed25519_sign']['p99_ms']} ms")
    print(f"  - Ed25519 Verify (p50 / p99): {c['ed25519_verify']['p50_ms']} ms / {c['ed25519_verify']['p99_ms']} ms")
    print(f"  - AES-256-GCM AEAD Rate     : {c['aes_256_gcm_throughput_mb_per_sec']} MB/s")

    print("\n[4] ASGI Server Engine (In-Memory HTTP):")
    s = results["server"]
    print(f"  - Cold Start Latency        : {s['cold_start_latency_ms']} ms")
    print(f"  - Warm p50 Latency          : {s['p50_ms']} ms")
    print(f"  - Warm p99 Latency          : {s['p99_ms']} ms")
    print(f"  - Request Rate              : {s['requests_per_sec']:,} req/sec")

    print("\n[5] Virtual Container Dataset Generation:")
    v = results["virtual_container"]
    for k, metrics in v.items():
        print(f"  - Workload: {k}")
        print(f"    * Generation Rate         : {metrics['generation_mb_per_sec']} MB/s")
        print(f"    * Persistence Rate        : {metrics['persistence_mb_per_sec']} MB/s")
        print(f"    * End-to-End Rate         : {metrics['end_to_end_mb_per_sec']} MB/s")
        print(f"    * Elapsed Duration        : {metrics['elapsed_seconds']} s")

    print("\n" + "=" * 70)
    print("  BENCHMARK COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
