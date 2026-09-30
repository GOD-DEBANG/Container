"""
resource_engine/storage_unit.py

Actual storage I/O measurement.

Benchmarks sequential read and write throughput for a given path
using the system's actual filesystem, block device, and OS cache
as they are configured — without assuming nominal disk specifications.

The benchmark writes a temporary file then reads it back, measuring
wall-clock throughput using time.perf_counter_ns().

Important limitation: OS filesystem cache can make read benchmarks
appear faster than actual disk throughput. This is reported in the
measurement metadata.
"""

from __future__ import annotations

import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class StorageMeasurement:
    """Snapshot of storage I/O performance."""
    timestamp_ns: int = 0
    path: str = ""

    # Sequential throughput
    write_bandwidth_bytes_per_second: Optional[float] = None
    read_bandwidth_bytes_per_second: Optional[float] = None

    benchmark_size_bytes: int = 0
    methodology: str = (
        "sequential write then read of a temporary file; "
        "may be inflated by OS filesystem cache"
    )
    unavailable_fields: list[str] = field(default_factory=list)


class StorageUnit:
    """Benchmarks actual storage throughput for a given directory."""

    # Default benchmark file size: 4 MiB (balances accuracy vs speed)
    DEFAULT_BENCHMARK_BYTES: int = 4 * 1024 * 1024
    _BLOCK_SIZE: int = 64 * 1024  # 64 KiB write/read blocks

    def __init__(self, benchmark_dir: Optional[Path] = None) -> None:
        self._dir = benchmark_dir or Path(tempfile.gettempdir())

    def measure(
        self, benchmark_size_bytes: int = DEFAULT_BENCHMARK_BYTES
    ) -> StorageMeasurement:
        """Run a write+read benchmark and return throughput."""
        m = StorageMeasurement(
            timestamp_ns=time.perf_counter_ns(),
            path=str(self._dir),
            benchmark_size_bytes=benchmark_size_bytes,
        )
        unavailable: list[str] = []

        try:
            write_bps = self._benchmark_write(benchmark_size_bytes)
            m.write_bandwidth_bytes_per_second = write_bps
        except Exception as e:
            unavailable.append(f"write_bandwidth ({e})")

        try:
            read_bps = self._benchmark_read(benchmark_size_bytes)
            m.read_bandwidth_bytes_per_second = read_bps
        except Exception as e:
            unavailable.append(f"read_bandwidth ({e})")

        m.unavailable_fields = unavailable
        return m

    def _benchmark_write(self, size_bytes: int) -> float:
        """Sequential write benchmark. Returns bytes/s."""
        data = bytes(self._BLOCK_SIZE)  # zero block
        with tempfile.NamedTemporaryFile(
            dir=self._dir, delete=False, suffix=".vcebench"
        ) as f:
            path = f.name
        try:
            written = 0
            start = time.perf_counter_ns()
            with open(path, "wb") as fh:
                while written < size_bytes:
                    chunk = min(self._BLOCK_SIZE, size_bytes - written)
                    fh.write(data[:chunk])
                    written += chunk
                fh.flush()
                os.fsync(fh.fileno())
            end = time.perf_counter_ns()
            elapsed_s = (end - start) / 1_000_000_000
            return written / elapsed_s if elapsed_s > 0 else 0.0
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    def _benchmark_read(self, size_bytes: int) -> float:
        """Sequential read benchmark. Returns bytes/s."""
        data = bytes(self._BLOCK_SIZE)
        with tempfile.NamedTemporaryFile(
            dir=self._dir, delete=False, suffix=".vcebench"
        ) as f:
            path = f.name
        try:
            # Write the file first
            written = 0
            with open(path, "wb") as fh:
                while written < size_bytes:
                    chunk = min(self._BLOCK_SIZE, size_bytes - written)
                    fh.write(data[:chunk])
                    written += chunk
                fh.flush()
                os.fsync(fh.fileno())

            # Read it back
            read_bytes = 0
            start = time.perf_counter_ns()
            with open(path, "rb") as fh:
                while True:
                    block = fh.read(self._BLOCK_SIZE)
                    if not block:
                        break
                    read_bytes += len(block)
            end = time.perf_counter_ns()
            elapsed_s = (end - start) / 1_000_000_000
            return read_bytes / elapsed_s if elapsed_s > 0 else 0.0
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
