"""
src/vdc/layer1_hierarchical/chunk_creator.py

Builds ChunkModel descriptors using pure offset arithmetic.
Does not allocate dataset payload bytes in memory.
"""

from __future__ import annotations

import uuid
from typing import Iterator, List

from ..models.chunk_model import ChunkModel, ChunkStatus


class ChunkCreator:
    @staticmethod
    def create_chunks(
        dataset_id: str,
        dataset_total_bytes: int,
        chunk_size_bytes: int,
    ) -> List[ChunkModel]:
        """
        Create all chunk descriptors for a dataset.
        Offsets and lengths strictly conserve dataset_total_bytes.
        """
        if dataset_total_bytes <= 0:
            raise ValueError(f"dataset_total_bytes must be > 0, got {dataset_total_bytes}")
        if chunk_size_bytes <= 0:
            raise ValueError(f"chunk_size_bytes must be > 0, got {chunk_size_bytes}")

        chunks: List[ChunkModel] = []
        offset = 0
        index = 0

        while offset < dataset_total_bytes:
            length = min(chunk_size_bytes, dataset_total_bytes - offset)
            chunk = ChunkModel(
                chunk_id=f"chk_{uuid.uuid4().hex[:12]}_{index}",
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
        offset = 0
        index = 0
        while offset < dataset_total_bytes:
            length = min(chunk_size_bytes, dataset_total_bytes - offset)
            yield ChunkModel(
                chunk_id=f"chk_{uuid.uuid4().hex[:12]}_{index}",
                dataset_id=dataset_id,
                chunk_index=index,
                byte_offset=offset,
                byte_length=length,
                status=ChunkStatus.ALLOCATED,
            )
            offset += length
            index += 1
