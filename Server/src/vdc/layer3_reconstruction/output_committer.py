"""
src/vdc/layer3_reconstruction/output_committer.py

Safely commits verified dataset from temporary storage to persistent storage.
Guarantees persisted files remain available after temporary container cleanup.
"""

from __future__ import annotations

import time
from typing import Tuple

from ..models.dataset_model import DatasetMetadata, DatasetSpec
from ..models.allocation_model import AllocationManifest
from ..storage.storage_interface import StorageInterface


class OutputCommitter:
    def __init__(
        self,
        temp_storage: StorageInterface,
        persistent_storage: StorageInterface,
        buffer_size: int = 65536,
    ) -> None:
        self.temp_storage = temp_storage
        self.persistent_storage = persistent_storage
        self.buffer_size = buffer_size

    def commit(
        self,
        spec: DatasetSpec,
        manifest: AllocationManifest,
        temp_dataset_path: str,
        actual_bytes: int,
        actual_records: int,
        checksum_sha256: str,
    ) -> Tuple[DatasetMetadata, str]:
        """
        Stream verified dataset from temporary storage into persistent storage.
        
        Returns:
            Tuple of (DatasetMetadata, persistent_file_path)
        """
        persistent_rel_path = f"datasets/{manifest.dataset_id}.bin"
        bytes_copied = 0

        with self.temp_storage.open_stream_reader(temp_dataset_path) as src:
            with self.persistent_storage.open_stream_writer(persistent_rel_path) as dst:
                while True:
                    chunk = src.read(self.buffer_size)
                    if not chunk:
                        break
                    dst.write(chunk)
                    bytes_copied += len(chunk)

        if bytes_copied != actual_bytes:
            raise IOError(f"Committer byte transfer mismatch: copied {bytes_copied}, expected {actual_bytes}")

        meta = DatasetMetadata(
            dataset_id=manifest.dataset_id,
            target_size_bytes=spec.target_size_bytes,
            actual_size_bytes=actual_bytes,
            actual_records=actual_records,
            checksum_sha256=checksum_sha256,
            chunk_count=len(manifest.chunks),
            subchunk_count=len(manifest.subchunks),
            storage_path=persistent_rel_path,
            created_at_utc=time.time(),
        )

        return meta, persistent_rel_path
