"""
cpu_engine/workload_benchmark.py

Benchmarks the actual processing workload (or a clearly identified
representative operation) using time.perf_counter_ns().

The benchmark:
  1. Runs the representative operation on a known-size byte buffer.
  2. Records elapsed nanoseconds.
  3. Repeats N times and takes the median throughput.
  4. Reports using V_measured = 8*B / T.

The representative workload for the initial processor is SHA-256
hashing, which matches the deterministic byte-preserving processor's
checksum computation. This is clearly labelled.
"""

from __future__ import annotations

import hashlib
import statistics
import time
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class BenchmarkResult:
    """Results from a workload benchmark run."""
    workload_label: str
    iterations: int
    bytes_per_iteration: int
    elapsed_ns_samples: list[int] = field(default_factory=list)
    median_elapsed_ns: int = 0
    median_throughput_bps: float = 0.0
    methodology: str = "V_measured = 8*B / T (perf_counter_ns, median of N runs)"
    error: str = ""

    @property
    def available(self) -> bool:
        return len(self.elapsed_ns_samples) > 0 and self.median_elapsed_ns > 0


class WorkloadBenchmark:
    """
    Benchmarks a workload by running it on a fixed-size buffer.

    The workload function must accept bytes and return bytes.
    It should represent the actual processing operation used on subchunks.
    """

    DEFAULT_BENCHMARK_SIZE: int = 256 * 1024   # 256 KiB
    DEFAULT_ITERATIONS: int = 5

    def __init__(
        self,
        workload_fn: Optional[Callable[[bytes], bytes]] = None,
        workload_label: str = "",
    ) -> None:
        if workload_fn is None:
            self._fn = self._sha256_passthrough
            self._label = "SHA-256 hash + passthrough (representative of checksum workload)"
        else:
            self._fn = workload_fn
            self._label = workload_label or "custom_workload"

    def run(
        self,
        benchmark_size_bytes: int = DEFAULT_BENCHMARK_SIZE,
        iterations: int = DEFAULT_ITERATIONS,
    ) -> BenchmarkResult:
        """
        Run the benchmark and return median throughput.
        Uses time.perf_counter_ns() for all timing.
        """
        result = BenchmarkResult(
            workload_label=self._label,
            iterations=iterations,
            bytes_per_iteration=benchmark_size_bytes,
        )

        try:
            data = self._generate_data(benchmark_size_bytes)
            samples: list[int] = []

            for _ in range(iterations):
                start = time.perf_counter_ns()
                _ = self._fn(data)
                end = time.perf_counter_ns()
                elapsed = end - start
                if elapsed > 0:
                    samples.append(elapsed)

            if not samples:
                result.error = "All benchmark iterations returned zero elapsed time"
                return result

            result.elapsed_ns_samples = samples
            result.median_elapsed_ns = int(statistics.median(samples))
            elapsed_s = result.median_elapsed_ns / 1_000_000_000
            result.median_throughput_bps = (benchmark_size_bytes * 8) / elapsed_s

        except Exception as exc:
            result.error = str(exc)

        return result

    @staticmethod
    def _sha256_passthrough(data: bytes) -> bytes:
        """Compute SHA-256 and return original data (byte-preserving)."""
        hashlib.sha256(data).hexdigest()
        return data

    @staticmethod
    def _generate_data(size_bytes: int) -> bytes:
        """Generate deterministic benchmark data."""
        import random
        rng = random.Random(42)
        return bytes(rng.randint(0, 255) for _ in range(size_bytes))
