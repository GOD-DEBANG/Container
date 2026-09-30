"""
layer1_hierarchical/chunk_creator.py

Creates ChunkModel descriptors for a dataset using streaming offsets.
Does NOT load dataset bytes into memory — only builds metadata.
"""

from __future__ import annotations

import uuid
from typing import Iterator

from models.chunk_model import ChunkModel, ChunkStatus


class ChunkCreator:
    """
    Builds ChunkModel descriptors by iterating over offset ranges.

    Conservation: sum(c.byte_length for c in chunks) == dataset_total_bytes.
    The last chunk may be smaller than chunk_size_bytes when the dataset
    size is not evenly divisible.
    """

    @staticmethod
    def create_chunks(
        dataset_id: str,
        dataset_total_bytes: int,
        chunk_size_bytes: int,
    ) -> list[ChunkModel]:
        """
        Create all chunk descriptors for a dataset.

        Uses streaming offset arithmetic — no byte arrays allocated.
        """
        if dataset_total_bytes <= 0:
            raise ValueError(f"dataset_total_bytes must be > 0, got {dataset_total_bytes}")
        if chunk_size_bytes <= 0:
            raise ValueError(f"chunk_size_bytes must be > 0, got {chunk_size_bytes}")

        chunks: list[ChunkModel] = []
        offset = 0
        index = 0

        while offset < dataset_total_bytes:
            length = min(chunk_size_bytes, dataset_total_bytes - offset)
            chunk = ChunkModel(
                chunk_id=str(uuid.uuid4()),
                dataset_id=dataset_id,
                chunk_index=index,
                byte_offset=offset,
                byte_length=length,
                status=ChunkStatus.ALLOCATED,
            )
            chunks.append(chunk)
            offset += length
            index += 1

        return chunks

    @staticmethod
    def iter_chunks(
        dataset_id: str,
        dataset_total_bytes: int,
        chunk_size_bytes: int,
    ) -> Iterator[ChunkModel]:
        """Generator version for memory-constrained usage."""
        offset = 0
        index = 0
        while offset < dataset_total_bytes:
            length = min(chunk_size_bytes, dataset_total_bytes - offset)
            yield ChunkModel(
                chunk_id=str(uuid.uuid4()),
                dataset_id=dataset_id,
                chunk_index=index,
                byte_offset=offset,
                byte_length=length,
                status=ChunkStatus.ALLOCATED,
            )
            offset += length
            index += 1
