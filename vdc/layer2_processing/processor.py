"""
src/vdc/layer2_processing/processor.py

Deterministic dataset record and byte generator/processor.
Generates reproducible byte sequences with cryptographically verified checksums.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass

from ..models.subchunk_model import SubchunkModel


@dataclass(frozen=True)
class SubchunkProcessingResult:
    subchunk_id: str
    chunk_id: str
    dataset_id: str
    data: bytes
    checksum_sha256: str
    byte_count: int
    record_count: int
    generation_seconds: float
    checksum_seconds: float


class DeterministicByteProcessor:
    """
    Generates deterministic pseudo-random bytes and structured records
    keyed by (dataset_seed, chunk_index, subchunk_index, byte_offset).
    """

    def __init__(self, seed: int = 42, record_size: int = 256) -> None:
        self.seed = seed
        self.record_size = max(16, record_size)

    def process_subchunk(self, subchunk: SubchunkModel) -> SubchunkProcessingResult:
        t0 = time.perf_counter()

        # Deterministic generation using keyed PRNG stream
        length = subchunk.byte_length
        # Fast deterministic pattern generation:
        # Mix seed, offset, index into deterministic byte patterns
        key_seed = (self.seed + subchunk.byte_offset + (subchunk.subchunk_index * 31)) & 0xFFFFFFFF
        
        # Build deterministic byte buffer
        # Using 64-byte repeated hash expansion block
        block_seed = f"VDC_{key_seed}_{subchunk.subchunk_id}".encode("ascii")
        base_hash = hashlib.sha256(block_seed).digest()
        
        # Fill requested length
        full_blocks = length // len(base_hash)
        remainder = length % len(base_hash)
        
        buf = bytearray()
        for i in range(full_blocks):
            # Deterministic variation per block
            block_variant = ((key_seed + i) & 0xFF).to_bytes(1, "big")
            buf.extend(base_hash[:-1] + block_variant)
        if remainder > 0:
            buf.extend(base_hash[:remainder])

        data = bytes(buf)
        t1 = time.perf_counter()

        # Compute SHA-256 checksum
        checksum = hashlib.sha256(data).hexdigest()
        t2 = time.perf_counter()

        record_count = max(1, length // self.record_size)

        return SubchunkProcessingResult(
            subchunk_id=subchunk.subchunk_id,
            chunk_id=subchunk.chunk_id,
            dataset_id=subchunk.dataset_id,
            data=data,
            checksum_sha256=checksum,
            byte_count=len(data),
            record_count=record_count,
            generation_seconds=(t1 - t0),
            checksum_seconds=(t2 - t1),
        )
