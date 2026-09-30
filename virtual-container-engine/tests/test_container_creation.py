"""
tests/test_container_creation.py
"""
import pytest
from pathlib import Path
from resource_engine.resource_budget import ResourceBudget, ExecutionPolicy
from container_core.container_factory import ContainerFactory

def test_container_creation_creates_unique_id(tmp_path: Path):
    budget = ResourceBudget.from_policy(ExecutionPolicy.BALANCED)
    
    with ContainerFactory.create(
        1024, 256, 64, 42, budget, tmp_path / "persist", tmp_path / "manifests"
    ) as c1:
        with ContainerFactory.create(
            1024, 256, 64, 42, budget, tmp_path / "persist", tmp_path / "manifests"
        ) as c2:
            assert c1.container_id != c2.container_id

def test_container_core_imports_without_output():
    # Should be able to import core without output module
    import container_core.virtual_container
    import sys
    assert "output.output_console" not in sys.modules
