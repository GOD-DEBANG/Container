"""
layer2_processing/processor.py

Abstract Processor interface and the initial BytePreservingProcessor.

The processor is injected into the container — it can be replaced
without modifying any core container file.

BytePreservingProcessor:
  - Reads input bytes.
  - Computes SHA-256 checksum.
  - Returns the original bytes unchanged.
  - This is a deterministic byte-preserving processor for testing.
  - It is explicitly labelled as such and does NOT claim to be an
    ML training engine or anything other than what it is.
"""

from __future__ import annotations

import hashlib
import time
from abc import ABC, abstractmethod

from models.subchunk_model import SubchunkModel
from models.processing_model import ProcessingResult, ProcessingStatus


class Processor(ABC):
    """
    Abstract processor interface.

    Implementations receive raw subchunk bytes and return processed bytes.
    The processor must be stateless or thread-safe.
    """

    @abstractmethod
    def process(
        self,
        subchunk: SubchunkModel,
        data: bytes,
        worker_id: str = "",
    ) -> ProcessingResult:
        """
        Process subchunk data.

        Returns a ProcessingResult with output checksum and timing.
        Must not raise exceptions — errors are returned in the result.
        """


class BytePreservingProcessor(Processor):
    """
    Deterministic byte-preserving processor.

    Behaviour:
      1. Validate input is non-empty bytes.
      2. Compute SHA-256 checksum of input.
      3. Return input bytes unchanged.
      4. Record nanosecond timing.

    This is the initial test processor.
    It is NOT an ML training engine, compression codec, encryption
    system, or any other transformation. It is explicitly a pass-through
    with checksum verification — suitable for testing the container
    lifecycle and reconstruction without data distortion.
    """

    label: str = "BytePreservingProcessor (SHA-256 checksum, pass-through)"

    def process(
        self,
        subchunk: SubchunkModel,
        data: bytes,
        worker_id: str = "",
    ) -> ProcessingResult:
        start_ns = time.perf_counter_ns()

        try:
            if not data:
                raise ValueError("Input data is empty")

            # Compute checksum (the actual CPU work done by this processor)
            checksum = hashlib.sha256(data).hexdigest()

            end_ns = time.perf_counter_ns()

            return ProcessingResult(
                subchunk_id=subchunk.subchunk_id,
                chunk_id=subchunk.chunk_id,
                dataset_id=subchunk.dataset_id,
                status=ProcessingStatus.SUCCESS,
                output_checksum=checksum,
                bytes_processed=len(data),
                elapsed_ns=end_ns - start_ns,
                worker_id=worker_id,
            )

        except Exception as exc:
            end_ns = time.perf_counter_ns()
            return ProcessingResult(
                subchunk_id=subchunk.subchunk_id,
                chunk_id=subchunk.chunk_id,
                dataset_id=subchunk.dataset_id,
                status=ProcessingStatus.FAILED,
                bytes_processed=0,
                elapsed_ns=end_ns - start_ns,
                worker_id=worker_id,
                error=str(exc),
            )
