"""
tests/test_resource_admission.py
"""
import pytest
from resource_engine.resource_admission import ResourceAdmission
from resource_engine.resource_budget import ResourceBudget
from resource_engine.resource_snapshot import ResourceSnapshot, CPUSnapshot, RAMSnapshot, StorageSnapshot

def test_memory_limits_prevent_unsafe_admission():
    # Budget explicitly set to 100MB
    budget = ResourceBudget(ram_budget_bytes=100 * 1024 * 1024)
    admission = ResourceAdmission(budget)
    
    # Process currently using 95MB
    snap = ResourceSnapshot(
        snapshot_id="test1",
        collected_at_ns=0,
        cpu=CPUSnapshot(process_cpu_percent=0.0),
        ram=RAMSnapshot(process_rss_bytes=95 * 1024 * 1024, system_total_bytes=1000 * 1024 * 1024),
        storage=StorageSnapshot(),
        active_workers=1
    )
    
    # Requesting to admit 10MB more work
    res = admission.check(snap, estimated_next_bytes=10 * 1024 * 1024, available_cores=1, system_ram_bytes=1000 * 1024 * 1024)
    
    # Should be denied because 95MB + 10MB > 100MB
    assert not res.admitted
    assert "RAM budget exceeded" in res.reasons_denied[0]

def test_resume_after_temporary_constraints():
    budget = ResourceBudget(ram_budget_bytes=100 * 1024 * 1024)
    admission = ResourceAdmission(budget)
    
    # Denied
    snap1 = ResourceSnapshot(
        snapshot_id="test2",
        collected_at_ns=0,
        cpu=CPUSnapshot(),
        ram=RAMSnapshot(process_rss_bytes=95 * 1024 * 1024),
        storage=StorageSnapshot(),
        active_workers=1
    )
    res1 = admission.check(snap1, estimated_next_bytes=10 * 1024 * 1024, available_cores=1, system_ram_bytes=1000 * 1024 * 1024)
    assert not res1.admitted
    
    # Memory drops to 50MB
    snap2 = ResourceSnapshot(
        snapshot_id="test3",
        collected_at_ns=0,
        cpu=CPUSnapshot(),
        ram=RAMSnapshot(process_rss_bytes=50 * 1024 * 1024),
        storage=StorageSnapshot(),
        active_workers=1
    )
    res2 = admission.check(snap2, estimated_next_bytes=10 * 1024 * 1024, available_cores=1, system_ram_bytes=1000 * 1024 * 1024)
    assert res2.admitted
