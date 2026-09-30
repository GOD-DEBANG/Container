"""
layer1_hierarchical/subchunk_creator.py

Creates SubchunkModel descriptors within a parent ChunkModel.
Does NOT load bytes — only builds metadata with streaming offsets.
"""

from __future__ import annotations

import uuid

from models.chunk_model import ChunkModel
from models.subchunk_model import SubchunkModel, SubchunkStatus


class SubchunkCreator:
    """
    Builds SubchunkModel descriptors for a given chunk.

    Conservation: sum(s.byte_length) == parent_chunk.byte_length.
    Byte offsets are absolute (within the full dataset).
    """

    @staticmethod
    def create_subchunks(
        chunk: ChunkModel,
        subchunk_size_bytes: int,
    ) -> list[SubchunkModel]:
        """
        Create all subchunk descriptors for a chunk.

        byte_offset of each subchunk is absolute within the full dataset.
        """
        if subchunk_size_bytes <= 0:
            raise ValueError(f"subchunk_size_bytes must be > 0, got {subchunk_size_bytes}")

        subchunks: list[SubchunkModel] = []
        offset = chunk.byte_offset
        index = 0
        remaining = chunk.byte_length

        while remaining > 0:
            length = min(subchunk_size_bytes, remaining)
            sub = SubchunkModel(
                subchunk_id=str(uuid.uuid4()),
                chunk_id=chunk.chunk_id,
                dataset_id=chunk.dataset_id,
                subchunk_index=index,
                byte_offset=offset,
                byte_length=length,
                status=SubchunkStatus.ALLOCATED,
            )
            subchunks.append(sub)
            offset += length
            remaining -= length
            index += 1

        return subchunks
