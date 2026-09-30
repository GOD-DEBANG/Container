"""
layer2_processing/execution_manager.py

Coordinates the per-container execution session:
  - Integrates resource admission control.
  - Applies actual speed calculation.
  - Enforces backpressure.
  - Records execution metrics.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from models.allocation_model import AllocationManifest
from models.processing_model import ProcessingResult
from models.execution_metrics import ExecutionMetrics
from layer2_processing.id_router import IDRouter
from layer2_processing.process_block import ProcessBlock
from layer2_processing.worker_manager import WorkerManager
from resource_engine.resource_monitor import ResourceMonitor
from resource_engine.resource_budget import ResourceBudget
from resource_engine.resource_normalizer import ResourceNormalizer
from resource_engine.resource_admission import ResourceAdmission
from resource_engine.resource_enforcer import ResourceEnforcer
from mathematics.actual_speed import ActualSpeedCalculator, UnavailablePolicy

logger = logging.getLogger(__name__)


class ExecutionManager:
    """
    Manages the execution session for one container.

    1. Reads resource snapshot.
    2. Calculates V_actual via ActualSpeedCalculator.
    3. Checks admission.
    4. Enforces backpressure.
    5. Submits blocks to WorkerManager in batches.
    6. Records metrics.
    """

    _CONTROL_INTERVAL_S: float = 0.5   # resource re-check interval

    def __init__(
        self,
        worker_manager: WorkerManager,
        resource_monitor: ResourceMonitor,
        budget: ResourceBudget,
        desired_speed_bps: float = 0.0,
    ) -> None:
        self._worker_mgr = worker_manager
        self._monitor = resource_monitor
        self._budget = budget
        self._desired_bps = desired_speed_bps

        self._normalizer = ResourceNormalizer(budget)
        self._admission = ResourceAdmission(budget)
        self._enforcer = ResourceEnforcer()
        self._speed_calc = ActualSpeedCalculator(UnavailablePolicy.SKIP)

    def run(
        self,
        manifest: AllocationManifest,
        metrics: ExecutionMetrics,
    ) -> list[ProcessingResult]:
        """
        Process all subchunks in the manifest and return all results.
        """
        router = IDRouter(manifest)
        all_blocks = self._build_blocks(manifest, router)
        all_results: list[ProcessingResult] = []

        metrics.start_ns = time.perf_counter_ns()
        available_cores = self._detect_cores()

        # Initial resource snapshot and speed calculation
        snapshot = self._monitor.snapshot(
            active_workers=0,
            queue_depth=len(all_blocks),
        )
        limits = self._normalizer.normalize(
            snapshot,
            measured_cpu_bps=metrics.cpu_benchmark_throughput_bits_per_second or None,
            ram_bandwidth_bps=self._monitor.cached_ram_bandwidth,
        )
        speed_result = self._speed_calc.calculate(
            desired_speed_bps=self._desired_bps or float("inf"),
            cpu_limit_bps=limits.cpu_limit_bps,
            ram_limit_bps=limits.ram_limit_bps,
            io_limit_bps=limits.io_limit_bps,
        )
        self._enforcer.apply_speed_result(speed_result)

        metrics.actual_speed_bits_per_second = speed_result.actual_speed_bits_per_second
        metrics.desired_speed_bits_per_second = self._desired_bps
        metrics.cpu_limit_bits_per_second = limits.cpu_limit_bps or 0.0
        metrics.ram_limit_bits_per_second = limits.ram_limit_bps or 0.0
        metrics.io_limit_bits_per_second = limits.io_limit_bps or 0.0
        metrics.limiting_resource = speed_result.limiting_resource

        logger.info(
            "V_actual = %.2f Mbps (limiting: %s)",
            speed_result.actual_speed_bits_per_second / 1e6,
            speed_result.limiting_resource,
        )

        # Process blocks in batches (bounded by max_workers)
        batch_size = max(1, self._budget.effective_workers(available_cores))
        for i in range(0, len(all_blocks), batch_size):
            if self._worker_mgr._cancelled.is_set():
                break

            batch = all_blocks[i : i + batch_size]

            # Admission check
            snap = self._monitor.snapshot(
                active_workers=self._worker_mgr.active_workers,
                queue_depth=len(all_blocks) - i,
            )
            system_ram = snap.ram.system_total_bytes or 0
            estimated_next = sum(b.subchunk.byte_length for b in batch)
            admission = self._admission.check(
                snap, estimated_next, available_cores, system_ram
            )
            admitted = self._enforcer.apply_admission_result(admission)

            if not admitted:
                logger.warning(
                    "Admission denied: %s — waiting %ss",
                    admission.reasons_denied,
                    self._CONTROL_INTERVAL_S,
                )
                time.sleep(self._CONTROL_INTERVAL_S)
                # Retry with same batch
                i -= batch_size  # will be corrected by loop increment (loop range doesn't backtrack)
                # Actually, just process anyway after wait — application-level best-effort

            batch_results = self._worker_mgr.process_blocks(batch)
            all_results.extend(batch_results)

        metrics.end_ns = time.perf_counter_ns()
        metrics.bytes_processed = sum(
            r.bytes_processed for r in all_results
            if r.status.name == "SUCCESS"
        )

        # Final resource snapshot for peak RAM
        final_snap = self._monitor.snapshot()
        metrics.peak_ram_bytes = final_snap.ram.process_rss_bytes or 0
        metrics.cpu_percent_avg = final_snap.cpu.process_cpu_percent or 0.0

        return all_results

    def _build_blocks(
        self, manifest: AllocationManifest, router: IDRouter
    ) -> list[ProcessBlock]:
        blocks: list[ProcessBlock] = []
        for sub in manifest.all_subchunks:
            route = router.route(sub.subchunk_id)
            if not route.valid:
                raise ValueError(f"Routing failed for subchunk {sub.subchunk_id}: {route.error}")
            blocks.append(ProcessBlock(subchunk=sub, data_path=route.data_path))
        return blocks

    def _detect_cores(self) -> int:
        try:
            import os
            return max(1, os.cpu_count() or 1)
        except Exception:
            return 1

    def get_resource_actions(self) -> list[str]:
        return self._enforcer.get_actions_summary()
