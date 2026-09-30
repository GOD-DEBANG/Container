"""
tests/test_reconstruction.py
"""
import pytest
from layer3_reconstruction.id_validator import IDValidator
from models.allocation_model import AllocationManifest
from models.chunk_model import ChunkModel, ChunkStatus
from models.subchunk_model import SubchunkModel, SubchunkStatus
from models.processing_model import ProcessingResult, ProcessingStatus

def create_mock_manifest() -> AllocationManifest:
    c = ChunkModel(chunk_id="c1", dataset_id="ds1", chunk_index=0, byte_offset=0, byte_length=100, status=ChunkStatus.ALLOCATED)
    s1 = SubchunkModel(subchunk_id="s1", chunk_id="c1", dataset_id="ds1", subchunk_index=0, byte_offset=0, byte_length=50, status=SubchunkStatus.ALLOCATED)
    s2 = SubchunkModel(subchunk_id="s2", chunk_id="c1", dataset_id="ds1", subchunk_index=1, byte_offset=50, byte_length=50, status=SubchunkStatus.ALLOCATED)
    return AllocationManifest(
        dataset_id="ds1",
        container_id="cnt1",
        dataset_total_bytes=100,
        chunks=[c],
        subchunks={"c1": [s1, s2]}
    )

def test_missing_chunks_fail_validation():
    manifest = create_mock_manifest()
    
    res1 = ProcessingResult(subchunk_id="s1", chunk_id="c1", dataset_id="ds1", status=ProcessingStatus.SUCCESS, bytes_processed=50, elapsed_ns=100)
    # s2 missing
    
    with pytest.raises(ValueError, match="Missing results for 1 subchunks"):
        IDValidator.validate_results(manifest, [res1])

def test_duplicate_chunks_fail_validation():
    manifest = create_mock_manifest()
    
    res1 = ProcessingResult(subchunk_id="s1", chunk_id="c1", dataset_id="ds1", status=ProcessingStatus.SUCCESS, bytes_processed=50, elapsed_ns=100)
    res2 = ProcessingResult(subchunk_id="s2", chunk_id="c1", dataset_id="ds1", status=ProcessingStatus.SUCCESS, bytes_processed=50, elapsed_ns=100)
    res1_dup = ProcessingResult(subchunk_id="s1", chunk_id="c1", dataset_id="ds1", status=ProcessingStatus.SUCCESS, bytes_processed=50, elapsed_ns=100)
    
    with pytest.raises(ValueError, match="Duplicate subchunk result: s1"):
        IDValidator.validate_results(manifest, [res1, res2, res1_dup])
