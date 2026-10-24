"""
src/vdc/layer2_processing/worker_manager.py

Coordinates subchunk processing workers and feeds output to temporary storage
while maintaining bounded in-memory queues and respecting pacing policies.
"""

from __future__ import annotations

import time
from typing import List, Dict

from ..models.subchunk_model import SubchunkModel, SubchunkStatus
from ..models.chunk_model import ChunkModel, ChunkStatus
from ..storage.storage_interface import StorageInterface
from .processor import DeterministicByteProcessor, SubchunkProcessingResult
from .bounded_queue import BoundedWorkQueue


class ProcessingWorkerManager:
    def __init__(
        self,
        processor: DeterministicByteProcessor,
        storage: StorageInterface,
        max_buffered_subchunks: int = 8,
    ) -> None:
        self.processor = processor
        self.storage = storage
        self.work_queue: BoundedWorkQueue[SubchunkModel] = BoundedWorkQueue(maxsize=max_buffered_subchunks)

    def process_chunk(
        self,
        chunk: ChunkModel,
        subchunks: List[SubchunkModel],
        pacing_delay_seconds: float = 0.0,
    ) -> Dict[str, str]:
        """
        Process all subchunks belonging to a single chunk.
        Appends subchunk data directly into a temporary chunk file in storage
        to guarantee bounded memory usage.
        
        Returns mapping of chunk_id -> storage path.
        """
        chunk.status = ChunkStatus.PROCESSING
        chunk_path = f"chunks/{chunk.chunk_id}.bin"
        
        total_records = 0
        total_bytes = 0

        with self.storage.open_stream_writer(chunk_path) as writer:
            for sub in subchunks:
                sub.status = SubchunkStatus.PROCESSING
                result: SubchunkProcessingResult = self.processor.process_subchunk(sub)
                
                # Write to storage stream
                writer.write(result.data)
                
                sub.status = SubchunkStatus.COMPLETED
                sub.checksum = result.checksum_sha256
                sub.record_count = result.record_count
                
                total_records += result.record_count
                total_bytes += result.byte_count

                if pacing_delay_seconds > 0.0:
                    time.sleep(pacing_delay_seconds)

        chunk.status = ChunkStatus.PROCESSED
        chunk.record_count = total_records

        return {chunk.chunk_id: chunk_path}
