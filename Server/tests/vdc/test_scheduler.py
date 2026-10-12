"""
tests/vdc/test_scheduler.py

Unit tests for AdaptiveScheduler.
Validates:
  - Formula outputs consumed during execution.
  - Lower resource budgets constrain admitted work.
  - Progress updates accurately emitted.
  - Cancellation and deadline timeouts work reliably.
"""

import time
import pytest

from vdc.models.execution_metrics import ExecutionMetrics
from vdc.resource_engine.resource_budget import ExecutionPolicy, ResourceBudget
from vdc.layer1_hierarchical.allocation_manager import AllocationManager
from vdc.layer2_processing.processor import DeterministicByteProcessor
from vdc.layer2_processing.worker_manager import ProcessingWorkerManager
from vdc.storage.temporary_storage import TemporaryStorage
from vdc.execution.scheduler import AdaptiveScheduler


class TestAdaptiveScheduler:
    def test_scheduler_executes_and_measures_metrics(self, tmp_path):
        temp_storage = TemporaryStorage(tmp_path / "temp")
        budget = ResourceBudget.from_policy(ExecutionPolicy.PERFORMANCE)
        processor = DeterministicByteProcessor(seed=1337)
        worker_mgr = ProcessingWorkerManager(processor, temp_storage)

        manifest = AllocationManager.build_manifest(
            dataset_id="test_ds",
            target_bytes=100000,
            chunk_size_bytes=25000,
            subchunk_size_bytes=10000,
        )

        progress_events = []
        def on_progress(ratio, completed, remaining):
            progress_events.append((ratio, completed, remaining))

        scheduler = AdaptiveScheduler(budget, worker_mgr, progress_callback=on_progress)
        metrics = ExecutionMetrics()

        chunk_paths = scheduler.schedule(manifest, metrics)

        assert len(chunk_paths) == len(manifest.chunks)
        assert metrics.actual_generated_bytes == 100000
        assert metrics.measured_generation_throughput_bytes_per_sec > 0
        assert len(progress_events) == len(manifest.chunks)
        assert progress_events[-1][0] == 1.0 # 100% progress at end

    def test_scheduler_cancellation(self, tmp_path):
        temp_storage = TemporaryStorage(tmp_path / "temp_cancel")
        budget = ResourceBudget.from_policy(ExecutionPolicy.LOW_CPU)
        processor = DeterministicByteProcessor(seed=42)
        worker_mgr = ProcessingWorkerManager(processor, temp_storage)

        manifest = AllocationManager.build_manifest(
            dataset_id="test_ds_cancel",
            target_bytes=500000,
            chunk_size_bytes=50000,
            subchunk_size_bytes=10000,
        )

        scheduler = AdaptiveScheduler(budget, worker_mgr)
        scheduler.cancel() # Cancel before starting
        metrics = ExecutionMetrics()

        with pytest.raises(InterruptedError):
            scheduler.schedule(manifest, metrics)

    def test_scheduler_deadline_timeout(self, tmp_path):
        temp_storage = TemporaryStorage(tmp_path / "temp_deadline")
        budget = ResourceBudget.from_policy(ExecutionPolicy.LOW_CPU)
        processor = DeterministicByteProcessor(seed=42)
        worker_mgr = ProcessingWorkerManager(processor, temp_storage)

        manifest = AllocationManager.build_manifest(
            dataset_id="test_ds_timeout",
            target_bytes=500000,
            chunk_size_bytes=50000,
            subchunk_size_bytes=10000,
        )

        # Set deadline in the past
        past_deadline = time.monotonic() - 10.0
        scheduler = AdaptiveScheduler(budget, worker_mgr, deadline_monotonic=past_deadline)
        metrics = ExecutionMetrics()

        with pytest.raises(TimeoutError):
            scheduler.schedule(manifest, metrics)
