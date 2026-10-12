"""
src/vdc/layer1_hierarchical/subchunk_creator.py

Builds SubchunkModel descriptors subdividing a ChunkModel.
"""

from __future__ import annotations

import uuid
from typing import Iterator, List

from ..models.chunk_model import ChunkModel
from ..models.subchunk_model import SubchunkModel, SubchunkStatus


class SubchunkCreator:
    @staticmethod
    def create_subchunks(
        chunk: ChunkModel,
        subchunk_size_bytes: int,
    ) -> List[SubchunkModel]:
        if subchunk_size_bytes <= 0:
            raise ValueError(f"subchunk_size_bytes must be > 0, got {subchunk_size_bytes}")

        subchunks: List[SubchunkModel] = []
        offset = 0
        index = 0

        while offset < chunk.byte_length:
            length = min(subchunk_size_bytes, chunk.byte_length - offset)
            subchunk = SubchunkModel(
                subchunk_id=f"sub_{uuid.uuid4().hex[:12]}_{chunk.chunk_index}_{index}",
                chunk_id=chunk.chunk_id,
                dataset_id=chunk.dataset_id,
                subchunk_index=index,
                byte_offset=chunk.byte_offset + offset,
                byte_length=length,
                status=SubchunkStatus.ALLOCATED,
            )
            subchunks.append(subchunk)
            offset += length
            index += 1

        return subchunks

    @staticmethod
    def iter_subchunks(
        chunk: ChunkModel,
        subchunk_size_bytes: int,
    ) -> Iterator[SubchunkModel]:
        offset = 0
        index = 0
        while offset < chunk.byte_length:
            length = min(subchunk_size_bytes, chunk.byte_length - offset)
            yield SubchunkModel(
                subchunk_id=f"sub_{uuid.uuid4().hex[:12]}_{chunk.chunk_index}_{index}",
                chunk_id=chunk.chunk_id,
                dataset_id=chunk.dataset_id,
                subchunk_index=index,
                byte_offset=chunk.byte_offset + offset,
                byte_length=length,
                status=SubchunkStatus.ALLOCATED,
            )
            offset += length
            index += 1
