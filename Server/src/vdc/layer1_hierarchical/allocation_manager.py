"""
src/vdc/layer1_hierarchical/allocation_manager.py

Orchestrates hierarchical dataset allocation and produces verified AllocationManifests.
"""

from __future__ import annotations

from typing import List

from ..models.allocation_model import AllocationManifest
from ..models.chunk_model import ChunkModel
from ..models.subchunk_model import SubchunkModel
from .chunk_creator import ChunkCreator
from .subchunk_creator import SubchunkCreator


class AllocationManager:
    @staticmethod
    def build_manifest(
        dataset_id: str,
        target_bytes: int,
        chunk_size_bytes: int,
        subchunk_size_bytes: int,
    ) -> AllocationManifest:
        chunks: List[ChunkModel] = ChunkCreator.create_chunks(
            dataset_id=dataset_id,
            dataset_total_bytes=target_bytes,
            chunk_size_bytes=chunk_size_bytes,
        )

        all_subchunks: List[SubchunkModel] = []
        for chk in chunks:
            subchunks = SubchunkCreator.create_subchunks(
                chunk=chk,
                subchunk_size_bytes=subchunk_size_bytes,
            )
            all_subchunks.extend(subchunks)

        manifest = AllocationManifest(
            dataset_id=dataset_id,
            target_bytes=target_bytes,
            chunks=chunks,
            subchunks=all_subchunks,
        )

        if not manifest.is_conserved():
            raise ValueError(
                f"Allocation conservation violation: target={target_bytes}, "
                f"chunks={manifest.total_chunk_bytes}, subchunks={manifest.total_subchunk_bytes}"
            )

        return manifest
