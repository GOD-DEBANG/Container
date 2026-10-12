"""
src/vdc/container_core/virtual_container.py

Virtual Container: An application-level lifecycle-managed dataset execution unit.
Executes the full container lifecycle:
  CREATED -> VALIDATING -> ALLOCATING -> PROCESSING -> RECONSTRUCTING ->
  VERIFYING -> PERSISTING -> COMPLETED -> DESTROYED
"""

from __future__ import annotations

import time
import uuid
from typing import Optional, Callable

from ..models.container_model import ContainerState
from ..models.dataset_model import DatasetSpec
from ..models.execution_metrics import ExecutionMetrics, ExecutionReport
from ..storage.temporary_storage import TemporaryStorage
from ..storage.persistent_storage import PersistentStorage
from ..resource_engine.resource_budget import ResourceBudget
from ..resource_engine.resource_admission import ResourceAdmissionController
from ..mathematics.throughput_formula import calculate_measured_throughput
from ..layer1_hierarchical.allocation_manager import AllocationManager
from ..layer2_processing.processor import DeterministicByteProcessor
from ..layer2_processing.worker_manager import ProcessingWorkerManager
from ..layer3_reconstruction.dataset_rebuilder import DatasetRebuilder
from ..layer3_reconstruction.integrity_validator import IntegrityValidator
from ..layer3_reconstruction.output_committer import OutputCommitter
from ..execution.scheduler import AdaptiveScheduler
from .lifecycle import LifecycleManager
from .cleanup import CleanupManager


class VirtualContainer:
    def __init__(
        self,
        container_id: str,
        job_id: str,
        spec: DatasetSpec,
        budget: ResourceBudget,
        temp_storage: TemporaryStorage,
        persistent_storage: PersistentStorage,
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        deadline_monotonic: Optional[float] = None,
    ) -> None:
        self.container_id = container_id
        self.job_id = job_id
        self.dataset_id = f"ds_{uuid.uuid4().hex[:12]}"
        self.spec = spec
        self.budget = budget
        self.temp_storage = temp_storage
        self.persistent_storage = persistent_storage
        self.progress_callback = progress_callback
        self.deadline_monotonic = deadline_monotonic

        self.lifecycle = LifecycleManager(ContainerState.CREATED)
        self.cleanup_manager = CleanupManager(temp_storage)
        self.metrics = ExecutionMetrics()
        self.scheduler: Optional[AdaptiveScheduler] = None

    def __enter__(self) -> VirtualContainer:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.destroy()

    def cancel(self) -> None:
        if self.scheduler:
            self.scheduler.cancel()
        if self.lifecycle.current_state not in (ContainerState.COMPLETED, ContainerState.DESTROYED):
            self.lifecycle.transition_to(ContainerState.CANCELLED)

    def run(self) -> ExecutionReport:
        """
        Execute full container lifecycle and return typed report.
        """
        self.metrics.start_time_monotonic = time.perf_counter()
        t_start = time.perf_counter()
        error_msg: Optional[str] = None
        storage_path: Optional[str] = None
        checksum: Optional[str] = None
        chunks_count = 0
        subchunks_count = 0

        try:
            # 1. VALIDATING
            self.lifecycle.transition_to(ContainerState.VALIDATING)
            admitted, reason = ResourceAdmissionController.check_admission(
                spec=self.spec,
                budget=self.budget,
            )
            if not admitted:
                self.lifecycle.transition_to(ContainerState.RESOURCE_BLOCKED)
                raise PermissionError(f"Resource admission rejected: {reason}")

            # 2. ALLOCATING
            self.lifecycle.transition_to(ContainerState.ALLOCATING)
            manifest = AllocationManager.build_manifest(
                dataset_id=self.dataset_id,
                target_bytes=self.spec.target_size_bytes,
                chunk_size_bytes=self.spec.chunk_size_bytes,
                subchunk_size_bytes=self.spec.subchunk_size_bytes,
            )
            chunks_count = len(manifest.chunks)
            subchunks_count = len(manifest.subchunks)

            # 3. PROCESSING
            self.lifecycle.transition_to(ContainerState.PROCESSING)
            processor = DeterministicByteProcessor(
                seed=self.spec.seed,
                record_size=self.spec.average_record_bytes,
            )
            worker_mgr = ProcessingWorkerManager(
                processor=processor,
                storage=self.temp_storage,
                max_buffered_subchunks=8,
            )
            self.scheduler = AdaptiveScheduler(
                budget=self.budget,
                worker_manager=worker_mgr,
                progress_callback=self.progress_callback,
                deadline_monotonic=self.deadline_monotonic,
            )

            chunk_paths = self.scheduler.schedule(manifest, self.metrics)

            # 4. RECONSTRUCTING
            self.lifecycle.transition_to(ContainerState.RECONSTRUCTING)
            t_rec_start = time.perf_counter()
            rebuilder = DatasetRebuilder(self.temp_storage)
            temp_output_path = f"datasets/{self.dataset_id}_temp.bin"
            rebuilt_bytes, calc_checksum = rebuilder.rebuild_dataset(
                manifest=manifest,
                chunk_paths=chunk_paths,
                output_relative_path=temp_output_path,
            )
            t_rec_end = time.perf_counter()
            self.metrics.reconstruction_seconds = t_rec_end - t_rec_start

            # 5. VERIFYING
            self.lifecycle.transition_to(ContainerState.VERIFYING)
            t_ver_start = time.perf_counter()
            from dataclasses import replace
            spec_to_verify = self.spec
            if self.spec.estimated_records <= 0:
                spec_to_verify = replace(self.spec, estimated_records=self.metrics.actual_records_generated)

            completion_report = IntegrityValidator.validate(
                spec=spec_to_verify,
                manifest=manifest,
                actual_bytes=rebuilt_bytes,
                actual_records=self.metrics.actual_records_generated,
                processed_chunk_ids=list(chunk_paths.keys()),
                output_verified=True,
            )
            t_ver_end = time.perf_counter()
            self.metrics.verification_seconds = t_ver_end - t_ver_start

            if not completion_report.is_complete:
                failures_str = "; ".join(completion_report.failure_reasons)
                raise AssertionError(f"Completion validation failed: {failures_str}")

            # 6. PERSISTING
            self.lifecycle.transition_to(ContainerState.PERSISTING)
            t_pers_start = time.perf_counter()
            committer = OutputCommitter(
                temp_storage=self.temp_storage,
                persistent_storage=self.persistent_storage,
            )
            dataset_meta, persistent_path = committer.commit(
                spec=self.spec,
                manifest=manifest,
                temp_dataset_path=temp_output_path,
                actual_bytes=rebuilt_bytes,
                actual_records=self.metrics.actual_records_generated,
                checksum_sha256=calc_checksum,
            )
            t_pers_end = time.perf_counter()
            pers_duration = max(1e-6, t_pers_end - t_pers_start)
            self.metrics.persistence_seconds = pers_duration
            self.metrics.actual_persisted_bytes = rebuilt_bytes
            self.metrics.measured_persistence_throughput_bytes_per_sec = calculate_measured_throughput(
                rebuilt_bytes, pers_duration
            )

            storage_path = persistent_path
            checksum = calc_checksum

            # 7. COMPLETED
            self.lifecycle.transition_to(ContainerState.COMPLETED)
            success = True

        except Exception as exc:
            success = False
            error_msg = str(exc)
            if self.lifecycle.current_state not in (ContainerState.CANCELLED, ContainerState.RESOURCE_BLOCKED):
                self.lifecycle.transition_to(ContainerState.FAILED)

        finally:
            self.metrics.end_time_monotonic = time.perf_counter()
            total_elapsed = max(1e-6, self.metrics.end_time_monotonic - t_start)
            self.metrics.total_elapsed_seconds = total_elapsed
            self.metrics.end_to_end_throughput_bytes_per_sec = calculate_measured_throughput(
                self.metrics.actual_generated_bytes, total_elapsed
            )

        return ExecutionReport(
            container_id=self.container_id,
            job_id=self.job_id,
            dataset_id=self.dataset_id,
            success=success,
            status=self.lifecycle.current_state.value,
            metrics=self.metrics,
            storage_path=storage_path,
            checksum_sha256=checksum,
            chunks_processed=chunks_count,
            subchunks_processed=subchunks_count,
            cleanup_successful=False,
            error=error_msg,
        )

    def destroy(self) -> bool:
        """
        Transition to DESTROYED and clean up temporary storage.
        """
        if self.lifecycle.current_state != ContainerState.DESTROYED:
            try:
                self.lifecycle.transition_to(ContainerState.DESTROYED)
            except ValueError:
                pass
        return self.cleanup_manager.perform_cleanup()
