"""
ml/dataset/generator.py
=======================
Adaptive Dataset Synthesizer and Multi-Modality Curator.
Supports numeric telemetry, container execution traces, and server event streams
with drift injection, anomaly labeling, and quality metrics reporting.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
import numpy as np


class AdaptiveDatasetSynthesizer:
    """
    Generates and curates multi-modal training and evaluation datasets:
    1. Numeric Telemetry (CPU, memory, IO, latency, queue)
    2. Container Execution Trace (chunk processing time, memory allocation, byte throughput, IO retries)
    3. Server Event Stream (request rate, active sessions, SSE connections, error rates, p99 latency)
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path(__file__).resolve().parent.parent / "data"
        self.raw_dir = self.output_dir / "raw"
        self.processed_dir = self.output_dir / "processed"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def generate_synthetic_telemetry_batch(
        self,
        n_samples: int = 1500,
        drift_factor: float = 0.0,
        anomaly_ratio: float = 0.08,
        seed: Optional[int] = 42
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """Numeric Telemetry Batch Generator."""
        if seed is not None:
            np.random.seed(seed)

        cpu = np.clip(np.random.normal(0.45 + drift_factor * 0.25, 0.18, size=n_samples), 0.0, 1.0)
        mem = np.clip(np.random.normal(0.50 + drift_factor * 0.20, 0.15, size=n_samples), 0.0, 1.0)
        io = np.clip(np.random.exponential(scale=0.3 + drift_factor * 0.15, size=n_samples), 0.0, 1.0)
        latency = np.random.normal(0.0 + drift_factor * 0.5, 1.0, size=n_samples)
        queue = np.random.poisson(lam=max(1, 3 + int(drift_factor * 5)), size=n_samples) / 15.0

        X = np.stack([cpu, mem, io, latency, queue], axis=1)
        risk_score = 0.3 * cpu + 0.3 * mem + 0.2 * io + 0.2 * np.tanh(latency) + 0.2 * queue
        clamped_ratio = max(0.001, min(0.5, anomaly_ratio))
        threshold = np.quantile(risk_score, 1.0 - clamped_ratio)
        y = (risk_score >= threshold).astype(int)

        feature_names = ["cpu_utilization", "memory_pressure", "io_throughput", "latency_zscore", "queue_depth"]
        metadata = self._build_metadata("numeric_telemetry", n_samples, feature_names, X, y, drift_factor, clamped_ratio)
        return X, y, metadata

    def generate_container_trace_batch(
        self,
        n_samples: int = 1500,
        drift_factor: float = 0.0,
        anomaly_ratio: float = 0.08,
        seed: Optional[int] = 42
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """Container Execution Trace Batch (Chunk throughput, chunk execution duration, heap MB, swap ops, retries)."""
        if seed is not None:
            np.random.seed(seed)

        chunk_mb = np.clip(np.random.normal(16.0 + drift_factor * 8.0, 4.0, size=n_samples), 1.0, 64.0)
        duration_ms = np.clip(np.random.exponential(scale=12.0 + drift_factor * 10.0, size=n_samples), 1.0, 250.0)
        heap_mb = np.clip(np.random.normal(128.0 + drift_factor * 64.0, 32.0, size=n_samples), 32.0, 512.0)
        swap_ops = np.random.poisson(lam=max(0, int(drift_factor * 8)), size=n_samples).astype(float)
        retries = np.random.binomial(n=3, p=min(0.8, 0.05 + drift_factor * 0.2), size=n_samples).astype(float)

        X = np.stack([chunk_mb, duration_ms, heap_mb, swap_ops, retries], axis=1)
        risk_score = (duration_ms / 100.0) + (heap_mb / 256.0) + (swap_ops * 0.4) + (retries * 0.6)
        clamped_ratio = max(0.001, min(0.5, anomaly_ratio))
        threshold = np.quantile(risk_score, 1.0 - clamped_ratio)
        y = (risk_score >= threshold).astype(int)

        feature_names = ["chunk_size_mb", "duration_ms", "heap_allocation_mb", "swap_operations", "io_retry_count"]
        metadata = self._build_metadata("container_execution_trace", n_samples, feature_names, X, y, drift_factor, clamped_ratio)
        return X, y, metadata

    def generate_server_stream_batch(
        self,
        n_samples: int = 1500,
        drift_factor: float = 0.0,
        anomaly_ratio: float = 0.08,
        seed: Optional[int] = 42
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """Server Event Stream Batch (Requests/sec, active SSE streams, p99 latency ms, 5xx error rate, auth cycles)."""
        if seed is not None:
            np.random.seed(seed)

        req_sec = np.clip(np.random.normal(1200.0 + drift_factor * 800.0, 300.0, size=n_samples), 10.0, 5000.0)
        sse_streams = np.clip(np.random.normal(45.0 + drift_factor * 30.0, 15.0, size=n_samples), 0.0, 200.0)
        p99_latency = np.clip(np.random.exponential(scale=4.5 + drift_factor * 6.0, size=n_samples), 0.5, 100.0)
        error_rate = np.clip(np.random.beta(0.5 + drift_factor, 20.0, size=n_samples), 0.0, 1.0)
        auth_cycles = np.random.poisson(lam=max(1, 15 + int(drift_factor * 20)), size=n_samples).astype(float)

        X = np.stack([req_sec, sse_streams, p99_latency, error_rate, auth_cycles], axis=1)
        risk_score = (p99_latency / 20.0) + (error_rate * 5.0) + (sse_streams / 100.0)
        clamped_ratio = max(0.001, min(0.5, anomaly_ratio))
        threshold = np.quantile(risk_score, 1.0 - clamped_ratio)
        y = (risk_score >= threshold).astype(int)

        feature_names = ["requests_per_sec", "active_sse_streams", "p99_latency_ms", "error_rate_pct", "auth_cycles_sec"]
        metadata = self._build_metadata("server_event_stream", n_samples, feature_names, X, y, drift_factor, clamped_ratio)
        return X, y, metadata

    def generate_by_modality(
        self,
        modality: str,
        n_samples: int = 1500,
        drift_factor: float = 0.0,
        anomaly_ratio: float = 0.08,
        seed: Optional[int] = 42
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """Dispatches generation according to chosen modality."""
        if modality == "container_execution_trace":
            return self.generate_container_trace_batch(n_samples, drift_factor, anomaly_ratio, seed)
        elif modality == "server_event_stream":
            return self.generate_server_stream_batch(n_samples, drift_factor, anomaly_ratio, seed)
        else:
            return self.generate_synthetic_telemetry_batch(n_samples, drift_factor, anomaly_ratio, seed)

    def _build_metadata(
        self,
        modality: str,
        n_samples: int,
        feature_names: List[str],
        X: np.ndarray,
        y: np.ndarray,
        drift: float,
        anomaly: float
    ) -> Dict[str, Any]:
        """Calculates statistical summary and metrics report."""
        stats = {}
        for idx, name in enumerate(feature_names):
            col = X[:, idx]
            stats[name] = {
                "mean": round(float(np.mean(col)), 4),
                "std": round(float(np.std(col)), 4),
                "min": round(float(np.min(col)), 4),
                "max": round(float(np.max(col)), 4),
            }

        return {
            "modality": modality,
            "n_samples": n_samples,
            "feature_dim": len(feature_names),
            "feature_names": feature_names,
            "drift_factor": drift,
            "target_anomaly_ratio": anomaly,
            "measured_anomaly_ratio": round(float(np.mean(y)), 4),
            "feature_statistics": stats,
            "timestamp_utc": str(Path(__file__).stat().st_mtime),
        }
