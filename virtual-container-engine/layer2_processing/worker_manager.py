"""
layer2_processing/worker_manager.py

Manages a pool of processing workers using concurrent.futures.ThreadPoolExecutor.

Responsibilities:
  - Enforce max_workers limit.
  - Submit ProcessBlocks to the pool.
  - Collect results.
  - Cancel or drain on shutdown.

Note: ThreadPoolExecutor is used instead of ProcessPoolExecutor to
avoid multiprocessing serialisation overhead for the byte-preserving
processor. For CPU-bound workloads that can GIL-release (e.g. via
numpy or C extensions), ProcessPoolExecutor may be substituted here
via dependency injection.
"""

from __future__ import annotations

import logging
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Callable

from models.processing_model import ProcessingResult, ProcessingStatus
from layer2_processing.process_block import ProcessBlock
from layer2_processing.processor import Processor
from storage.storage_interface import StorageInterface

logger = logging.getLogger(__name__)


class WorkerManager:
    """
    Thread-pool–based worker manager with configurable concurrency.

    max_workers is enforced by the ThreadPoolExecutor.
    Additional admission control is provided by ResourceAdmission.
    """

    _SENTINEL = None  # queue sentinel for shutdown

    def __init__(
        self,
        processor: Processor,
        storage: StorageInterface,
        max_workers: int = 1,
    ) -> None:
        self._processor = processor
        self._storage = storage
        self._max_workers = max(1, max_workers)
        self._cancelled = threading.Event()
        self._active_count = 0
        self._lock = threading.Lock()

    @property
    def active_workers(self) -> int:
        with self._lock:
            return self._active_count

    def cancel(self) -> None:
        self._cancelled.set()

    def process_blocks(
        self, blocks: list[ProcessBlock]
    ) -> list[ProcessingResult]:
        """
        Process all blocks using the thread pool.
        Returns results — possibly out of submission order.

        If cancellation is requested, remaining blocks are returned
        with CANCELLED status.
        """
        results: list[ProcessingResult] = []
        futures: dict[Future[ProcessingResult], ProcessBlock] = {}

        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            for block in blocks:
                if self._cancelled.is_set():
                    results.append(
                        ProcessingResult(
                            subchunk_id=block.subchunk.subchunk_id,
                            chunk_id=block.subchunk.chunk_id,
                            dataset_id=block.subchunk.dataset_id,
                            status=ProcessingStatus.CANCELLED,
                            error="Cancelled before processing started",
                        )
                    )
                    continue

                worker_id = str(uuid.uuid4())[:8]
                block.worker_id = worker_id
                future = pool.submit(self._execute_block, block, worker_id)
                futures[future] = block

                with self._lock:
                    self._active_count += 1

            for future in as_completed(futures):
                block = futures[future]
                try:
                    result = future.result()
                    block.result = result
                    results.append(result)
                except Exception as exc:
                    result = ProcessingResult(
                        subchunk_id=block.subchunk.subchunk_id,
                        chunk_id=block.subchunk.chunk_id,
                        dataset_id=block.subchunk.dataset_id,
                        status=ProcessingStatus.FAILED,
                        error=str(exc),
                        worker_id=block.worker_id,
                    )
                    block.result = result
                    results.append(result)
                finally:
                    with self._lock:
                        self._active_count -= 1

        return results

    def _execute_block(
        self, block: ProcessBlock, worker_id: str
    ) -> ProcessingResult:
        """Execute one ProcessBlock. Runs in a worker thread."""
        if self._cancelled.is_set():
            return ProcessingResult(
                subchunk_id=block.subchunk.subchunk_id,
                chunk_id=block.subchunk.chunk_id,
                dataset_id=block.subchunk.dataset_id,
                status=ProcessingStatus.CANCELLED,
                error="Cancelled",
                worker_id=worker_id,
            )

        # Load bytes from storage (only now — not before)
        data = self._storage.read(block.data_path)

        # Write processed output back to storage
        result = self._processor.process(block.subchunk, data, worker_id)

        if result.status == ProcessingStatus.SUCCESS:
            out_path = block.data_path.replace(".bin", ".proc.bin")
            self._storage.write(out_path, data)  # byte-preserving: same data
            logger.debug(
                "Worker %s processed subchunk %s in %.3f ms",
                worker_id,
                block.subchunk.subchunk_id[:8],
                result.elapsed_ns / 1_000_000,
            )

        return result
