"""
src/vdc/layer3_reconstruction/dataset_rebuilder.py

Reconstructs the full dataset in logical sequential order from processed chunks.
Uses bounded streaming buffer transfers to avoid loading the full dataset into RAM.
"""

from __future__ import annotations

import hashlib
from typing import Dict, Tuple

from ..models.allocation_model import AllocationManifest
from ..models.chunk_model import ChunkStatus
from ..storage.storage_interface import StorageInterface


class DatasetRebuilder:
    def __init__(self, storage: StorageInterface, stream_buffer_bytes: int = 65536) -> None:
        self.storage = storage
        self.buffer_size = max(4096, stream_buffer_bytes)

    def rebuild_dataset(
        self,
        manifest: AllocationManifest,
        chunk_paths: Dict[str, str],
        output_relative_path: str,
    ) -> Tuple[int, str]:
        """
        Stream all chunks in index order into output_relative_path.
        Calculates SHA-256 checksum on the fly.
        
        Returns:
            Tuple of (total_bytes_written, sha256_checksum)
        """
        # Sort chunks strictly by chunk_index
        sorted_chunks = sorted(manifest.chunks, key=lambda c: c.chunk_index)

        hasher = hashlib.sha256()
        total_written = 0

        with self.storage.open_stream_writer(output_relative_path) as out_writer:
            for chk in sorted_chunks:
                if chk.chunk_id not in chunk_paths:
                    raise ValueError(f"Missing storage path for chunk {chk.chunk_id} (index {chk.chunk_index})")
                
                path = chunk_paths[chk.chunk_id]
                chunk_bytes_read = 0

                with self.storage.open_stream_reader(path) as chunk_reader:
                    while True:
                        block = chunk_reader.read(self.buffer_size)
                        if not block:
                            break
                        hasher.update(block)
                        out_writer.write(block)
                        chunk_bytes_read += len(block)
                        total_written += len(block)

                if chunk_bytes_read != chk.byte_length:
                    raise ValueError(
                        f"Chunk {chk.chunk_index} size mismatch: read {chunk_bytes_read} bytes, "
                        f"expected {chk.byte_length} bytes"
                    )

                chk.status = ChunkStatus.VERIFIED

        checksum = hasher.hexdigest()
        return total_written, checksum
