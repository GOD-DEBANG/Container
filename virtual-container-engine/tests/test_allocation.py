"""
tests/test_allocation.py
"""
import pytest
from layer1_hierarchical.chunk_creator import ChunkCreator
from layer1_hierarchical.subchunk_creator import SubchunkCreator

def test_allocation_totals_equal_dataset_target():
    dataset_id = "test-dataset-id"
    target_size = 10_000_000
    chunk_size = 1_000_000
    subchunk_size = 250_000
    
    chunks = ChunkCreator.create_chunks(dataset_id, target_size, chunk_size)
    assert sum(c.byte_length for c in chunks) == target_size
    
    total_subchunk_bytes = 0
    for chunk in chunks:
        subs = SubchunkCreator.create_subchunks(chunk, subchunk_size)
        chunk_sub_bytes = sum(s.byte_length for s in subs)
        assert chunk_sub_bytes == chunk.byte_length
        total_subchunk_bytes += chunk_sub_bytes
        
    assert total_subchunk_bytes == target_size

def test_uneven_allocation_totals():
    dataset_id = "test-dataset-id"
    target_size = 1_000_005  # Uneven
    chunk_size = 300_000
    subchunk_size = 100_000
    
    chunks = ChunkCreator.create_chunks(dataset_id, target_size, chunk_size)
    assert sum(c.byte_length for c in chunks) == target_size
    assert chunks[-1].byte_length == 100_005
    
    subs = SubchunkCreator.create_subchunks(chunks[-1], subchunk_size)
    assert sum(s.byte_length for s in subs) == chunks[-1].byte_length
    assert subs[-1].byte_length == 5
