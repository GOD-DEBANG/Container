"""
tests/vdc/test_container.py

Unit tests for VirtualContainer lifecycle, reconstruction, and cleanup guarantees.
"""


from vdc.models.dataset_model import DatasetSpec
from vdc.models.container_model import ContainerState
from vdc.resource_engine.resource_budget import ExecutionPolicy, ResourceBudget
from vdc.container_core.factory import ContainerFactory


class TestVirtualContainer:
    def test_container_end_to_end_lifecycle_and_cleanup(self, tmp_path):
        temp_dir = tmp_path / "temp_run"
        persistent_dir = tmp_path / "persistent_out"
        budget = ResourceBudget.from_policy(ExecutionPolicy.PERFORMANCE)

        spec = DatasetSpec(
            target_size_bytes=200000,
            chunk_size_bytes=50000,
            subchunk_size_bytes=10000,
            seed=777,
        )

        with ContainerFactory.create(
            job_id="test_job_1",
            spec=spec,
            budget=budget,
            persistent_storage_dir=persistent_dir,
            temp_base_dir=temp_dir,
        ) as container:
            assert container.lifecycle.current_state == ContainerState.CREATED
            report = container.run()

            assert report.success is True
            assert report.status == ContainerState.COMPLETED.value
            assert report.metrics.actual_generated_bytes == 200000
            assert report.metrics.actual_persisted_bytes == 200000
            assert report.checksum_sha256 is not None
            assert report.storage_path is not None

            # Verify persisted file exists
            persisted_file = persistent_dir / report.storage_path
            assert persisted_file.exists()
            assert persisted_file.stat().st_size == 200000

        # After exiting context manager: container.destroy() was called
        # Verify temporary directory was wiped
        temp_container_dir = temp_dir / container.container_id
        assert not temp_container_dir.exists()

        # Verify persistent dataset survived container destruction!
        assert persisted_file.exists()
        assert persisted_file.stat().st_size == 200000

    def test_unique_container_per_job(self, tmp_path):
        budget = ResourceBudget.from_policy(ExecutionPolicy.BALANCED)
        spec = DatasetSpec(target_size_bytes=1000, chunk_size_bytes=500, subchunk_size_bytes=250)

        c1 = ContainerFactory.create("job_1", spec, budget, tmp_path / "out")
        c2 = ContainerFactory.create("job_2", spec, budget, tmp_path / "out")

        assert c1.container_id != c2.container_id
        c1.destroy()
        c2.destroy()

    def test_resource_admission_rejection(self, tmp_path):
        budget = ResourceBudget.from_policy(ExecutionPolicy.BALANCED)
        # Exceeds max safe limit (256 MB)
        oversized_spec = DatasetSpec(
            target_size_bytes=500 * 1024 * 1024, # 500 MB
            chunk_size_bytes=10 * 1024 * 1024,
            subchunk_size_bytes=2 * 1024 * 1024,
        )

        with ContainerFactory.create("huge_job", oversized_spec, budget, tmp_path / "out") as c:
            report = c.run()
            assert report.success is False
            assert report.error is not None and "rejected" in report.error.lower()
            assert c.lifecycle.current_state == ContainerState.RESOURCE_BLOCKED
