"""
tests/test_cleanup.py
"""
import pytest
from pathlib import Path
from resource_engine.resource_budget import ResourceBudget, ExecutionPolicy
from container_core.virtual_container import VirtualContainer
from models.container_model import ContainerState

def test_failed_generation_triggers_cleanup(tmp_path: Path):
    budget = ResourceBudget.from_policy(ExecutionPolicy.BALANCED)
    
    container = VirtualContainer(
        target_size_bytes=1024,
        chunk_size_bytes=256,
        subchunk_size_bytes=64,
        seed=42,
        budget=budget,
        persistent_storage_dir=tmp_path / "persist",
        manifest_dir=tmp_path / "manifests"
    )
    
    # Force failure
    container.initialize()
    # Transition to invalid state to cause run() to fail
    container._lifecycle.transition(ContainerState.COMPLETED)
    
    report = container.run()
    
    assert report.status == "FAILED"
    
    # We must explicitly call destroy because we are not using the factory context manager in this test
    container.destroy()
    
    assert container.state == ContainerState.DESTROYED
    # temp path should be removed
    assert not container._temp_storage.root().exists()
