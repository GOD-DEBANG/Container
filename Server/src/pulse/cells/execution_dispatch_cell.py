"""
src/pulse/cells/execution_dispatch_cell.py

Container Execution Dispatch Cell.
Executes bounded jobs INLINE inside the active invocation, or submits
to DURABLE_WORKER when configured.
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional

from ..core.pipeline import BaseCell, PulseContext
from ..core.pulse import Pulse
from ..fabric.store_interface import StoreInterface
from vdc.services.dataset_generation_service import DatasetGenerationService
from vdc.resource_engine.resource_budget import ExecutionPolicy


class ExecutionDispatchCell(BaseCell):
    name = "ExecutionDispatchCell"
    input_contract = Pulse
    output_contract = Pulse

    def __init__(
        self,
        store: StoreInterface,
        generation_service: Optional[DatasetGenerationService] = None,
        max_duration_seconds: float = 120.0,
    ) -> None:
        self.store = store
        self.generation_service = generation_service or DatasetGenerationService()
        self.max_duration_seconds = max_duration_seconds

    async def process(self, context: PulseContext) -> PulseContext:
        job_id = context.state.get("job_id")
        params = context.state.get("validated_params", {})
        backend = params.get("backend", "INLINE")

        if backend == "INLINE":
            # Progress callback bridge that writes events into StoreInterface
            loop = asyncio.get_running_loop()

            def sync_progress_callback(ratio: float, completed: int, remaining: int) -> None:
                # Schedule async event write onto running loop
                ev = {
                    "event_type": "pulse_progress",
                    "job_id": job_id,
                    "progress_ratio": ratio,
                    "completed_bytes": completed,
                    "remaining_bytes": remaining,
                    "timestamp": time.time(),
                }
                asyncio.run_coroutine_threadsafe(self.store.append_event(job_id, ev), loop)

            deadline = time.monotonic() + self.max_duration_seconds
            policy = ExecutionPolicy(params.get("policy", "BALANCED"))

            # Execute in thread executor to keep async event loop responsive
            report = await loop.run_in_executor(
                None,
                lambda: self.generation_service.generate(
                    job_id=job_id,
                    target_size_bytes=params["target_size_bytes"],
                    chunk_size_bytes=params["chunk_size_bytes"],
                    subchunk_size_bytes=params["subchunk_size_bytes"],
                    seed=params["seed"],
                    policy=policy,
                    progress_callback=sync_progress_callback,
                    deadline_monotonic=deadline,
                ),
            )

            job_status = "COMPLETED" if report.success else "FAILED"
            final_job_data = {
                "status": job_status,
                "dataset_id": report.dataset_id,
                "container_id": report.container_id,
                "storage_path": report.storage_path,
                "checksum_sha256": report.checksum_sha256,
                "chunks_processed": report.chunks_processed,
                "subchunks_processed": report.subchunks_processed,
                "error": report.error,
                "metrics": {
                    "actual_generated_bytes": report.metrics.actual_generated_bytes,
                    "actual_persisted_bytes": report.metrics.actual_persisted_bytes,
                    "total_elapsed_seconds": report.metrics.total_elapsed_seconds,
                    "generation_throughput_bps": report.metrics.measured_generation_throughput_bytes_per_sec,
                    "persistence_throughput_bps": report.metrics.measured_persistence_throughput_bytes_per_sec,
                    "limiting_resource": report.metrics.limiting_resource,
                },
                "updated_at_utc": time.time(),
            }

            await self.store.save_job(job_id, final_job_data)
            await self.store.append_event(
                job_id,
                {
                    "event_type": "pulse_completed" if report.success else "pulse_failed",
                    "job_id": job_id,
                    "status": job_status,
                    "error": report.error,
                    "timestamp": time.time(),
                },
            )

            context.state["execution_report"] = report
            context.state["final_job_data"] = final_job_data

        elif backend == "DURABLE_WORKER":
            # For durable worker mode, job is enqueued
            update = {
                "status": "QUEUED_DURABLE",
                "queue_name": "pulse-jobs-durable",
                "updated_at_utc": time.time(),
            }
            await self.store.save_job(job_id, update)
            context.state["final_job_data"] = update

        return context
