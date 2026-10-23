"""
src/pulse/observability/metrics.py

Metrics collector for request latency, error rates, percentiles (p50, p99),
and container execution throughput.
"""

from __future__ import annotations

import math
import threading
from typing import Any, Dict, List


class MetricsRegistry:
    def __init__(self) -> None:
        self._counters: Dict[str, int] = {}
        self._latencies: Dict[str, List[float]] = {}
        self._gauges: Dict[str, float] = {}
        self._lock = threading.Lock()

    def increment(self, metric_name: str, count: int = 1) -> None:
        with self._lock:
            self._counters[metric_name] = self._counters.get(metric_name, 0) + count

    def set_gauge(self, metric_name: str, value: float) -> None:
        with self._lock:
            self._gauges[metric_name] = value

    def record_latency(self, metric_name: str, latency_seconds: float) -> None:
        with self._lock:
            bucket = self._latencies.setdefault(metric_name, [])
            bucket.append(latency_seconds)
            # Keep rolling window of last 2000 samples
            if len(bucket) > 2000:
                self._latencies[metric_name] = bucket[-2000:]

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            summary: Dict[str, Any] = {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "latencies": {},
            }
            for name, values in self._latencies.items():
                if not values:
                    continue
                sorted_vals = sorted(values)
                n = len(sorted_vals)
                p50 = sorted_vals[math.ceil(0.50 * n) - 1]
                p99 = sorted_vals[math.ceil(0.99 * n) - 1]
                avg = sum(sorted_vals) / n
                summary["latencies"][name] = {
                    "count": n,
                    "avg_ms": round(avg * 1000, 3),
                    "p50_ms": round(p50 * 1000, 3),
                    "p99_ms": round(p99 * 1000, 3),
                }
            return summary


metrics = MetricsRegistry()
