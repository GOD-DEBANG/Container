"""
container_core/virtual_container.py

The core engine object. Ties together all 3 layers and the execution state.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from models.container_model import ContainerState
from models.dataset_model import DatasetModel
from models.allocation_model import AllocationManifest
from models.processing_model import ProcessingResult
from models.execution_metrics import ExecutionMetrics, ExecutionReport
from container_core.container_lifecycle import ContainerLifecycle
from container_core.execution_guard import ExecutionGuard
from container_core.resource_manager import ResourceManager
from container_core.cleanup_manager import CleanupManager
from layer1_hierarchical.hierarchical_layer import HierarchicalLayer
from layer2_processing.processing_layer import ProcessingLayer
from layer3_reconstruction.refactoring_layer import RefactoringLayer
from layer2_processing.processor import BytePreservingProcessor
from storage.temporary_storage import TemporaryStorage
from storage.persistent_storage import PersistentStorage
from storage.manifest_manager import ManifestManager
from resource_engine.resource_budget import ResourceBudget

logger = logging.getLogger(__name__)


class VirtualContainer:
    """
    Virtual Container Engine Core Object.
    
    Each instance represents exactly one dataset generation request.
    It manages its own state, temporary storage, and lifecycle.
    """

    def __init__(
        self,
        target_size_bytes: int,
        chunk_size_bytes: int,
        subchunk_size_bytes: int,
        seed: int,
        budget: ResourceBudget,
        persistent_storage_dir: Path,
        manifest_dir: Path,
    ) -> None:
        self.container_id = str(uuid.uuid4())
        
        # Core configuration
        self._target_size_bytes = target_size_bytes
        self._chunk_size_bytes = chunk_size_bytes
        self._subchunk_size_bytes = subchunk_size_bytes
        self._seed = seed
        self._budget = budget
        
        # State Management
        self._lifecycle = ContainerLifecycle()
        self._metrics = ExecutionMetrics()
        self._error_message = ""
        
        # Infrastructure
        self._temp_storage = TemporaryStorage(self.container_id)
        self._persistent_storage = PersistentStorage(persistent_storage_dir)
        self._manifest_manager = ManifestManager(manifest_dir)
        self._resource_manager = ResourceManager(self._temp_storage.root())
        
        # Output State
        self._manifest: AllocationManifest | None = None
        self._processing_results: list[ProcessingResult] | None = None
        self._final_dataset_path: Path | None = None
        self._integrity_verified = False
        self._dataset_checksum = ""
        
        # Subsystems
        self._layer1 = HierarchicalLayer(self._temp_storage, self._manifest_manager)
        self._layer2 = ProcessingLayer(
            processor=BytePreservingProcessor(),
            storage=self._temp_storage,
            resource_monitor=self._resource_manager.monitor,
        )
        self._layer3 = RefactoringLayer(self._temp_storage, self._persistent_storage)

        logger.info("Created VirtualContainer %s", self.container_id)

    @property
    def state(self) -> ContainerState:
        return self._lifecycle.state
        
    @ExecutionGuard.require_state(ContainerState.CREATED)
    def initialize(self) -> None:
        """Initialize resources and warm up benchmarks."""
        logger.info("Container %s initializing", self.container_id)
        try:
            self._resource_manager.initialize()
            self._lifecycle.transition(ContainerState.INITIALIZED)
        except Exception as e:
            self._fail(f"Initialization error: {e}")

    @ExecutionGuard.require_state(ContainerState.INITIALIZED)
    def allocate(self) -> None:
        """Run Layer 1: Hierarchical allocation."""
        self._lifecycle.transition(ContainerState.ALLOCATING)
        try:
            self._manifest = self._layer1.run(
                container_id=self.container_id,
                target_size_bytes=self._target_size_bytes,
                chunk_size_bytes=self._chunk_size_bytes,
                subchunk_size_bytes=self._subchunk_size_bytes,
                seed=self._seed,
            )
            # Store some metrics
            self._metrics.chunk_count = self._manifest.chunk_count
            self._metrics.subchunk_count = self._manifest.subchunk_count
            
        except Exception as e:
            self._fail(f"Allocation error: {e}")

    @ExecutionGuard.require_state(ContainerState.ALLOCATING)
    def process(self) -> None:
        """Run Layer 2: Processing."""
        self._lifecycle.transition(ContainerState.PROCESSING)
        try:
            if not self._manifest:
                raise RuntimeError("Manifest missing during processing")
                
            self._processing_results = self._layer2.run(
                manifest=self._manifest,
                metrics=self._metrics,
                budget=self._budget,
            )
        except Exception as e:
            self._fail(f"Processing error: {e}")

    @ExecutionGuard.require_state(ContainerState.PROCESSING)
    def reconstruct(self) -> None:
        """Run Layer 3: Reconstruction."""
        self._lifecycle.transition(ContainerState.RECONSTRUCTING)
        try:
            if not self._manifest or not self._processing_results:
                raise RuntimeError("Missing dependencies for reconstruction")
            
            # The refactoring layer handles Reconstruct -> Validate -> Commit
            valid, checksum, output_path = self._layer3.run(
                manifest=self._manifest,
                results=self._processing_results,
            )
            
            # Since the layer did everything, we can jump state
            self._lifecycle.transition(ContainerState.VALIDATING)
            self._integrity_verified = valid
            self._dataset_checksum = checksum
            
            self._lifecycle.transition(ContainerState.COMMITTING)
            self._final_dataset_path = output_path
            
            self._lifecycle.transition(ContainerState.COMPLETED)
            
        except Exception as e:
            self._fail(f"Reconstruction error: {e}")

    def run(self) -> ExecutionReport:
        """Run the full container lifecycle."""
        try:
            if self.state == ContainerState.CREATED:
                self.initialize()
            if self.state == ContainerState.INITIALIZED:
                self.allocate()
            if self.state == ContainerState.ALLOCATING:
                self.process()
            if self.state == ContainerState.PROCESSING:
                self.reconstruct()
        except Exception as e:
            if self.state not in (ContainerState.FAILED, ContainerState.CANCELLED):
                self._fail(f"Unexpected run error: {e}")
                
        return self._generate_report()

    def cancel(self) -> None:
        """Cancel container execution."""
        if self.state in (ContainerState.COMPLETED, ContainerState.FAILED, ContainerState.DESTROYED):
            return
            
        logger.info("Cancelling container %s", self.container_id)
        try:
            self._lifecycle.transition(ContainerState.CANCELLED)
        except ValueError:
            pass # Invalid transition handled by state machine
            
        self._error_message = "Execution cancelled by caller"

    def destroy(self) -> None:
        """Destroy container resources."""
        if self.state == ContainerState.DESTROYED:
            return
            
        logger.info("Destroying container %s", self.container_id)
        CleanupManager.cleanup(
            container_id=self.container_id,
            temp_storage=self._temp_storage,
            processing_layer=self._layer2,
        )
        
        # Force transition to destroyed, regardless of prior state
        self._lifecycle._state = ContainerState.DESTROYED
        
        from container_core.container_registry import ContainerRegistry
        ContainerRegistry.get_instance().unregister(self.container_id)

    def _fail(self, reason: str) -> None:
        """Handle execution failure."""
        logger.error("Container %s failed: %s", self.container_id, reason)
        self._error_message = reason
        try:
            self._lifecycle.transition(ContainerState.FAILED)
        except ValueError:
            pass
        raise RuntimeError(reason)

    def _generate_report(self) -> ExecutionReport:
        dataset_id = self._manifest.dataset_id if self._manifest else "unknown"
        allocated = self._manifest.dataset_total_bytes if self._manifest else 0
        processed = self._metrics.bytes_processed
        
        # Populate resource report fields
        cpu_snap = self._resource_manager.monitor.snapshot().cpu
        
        return ExecutionReport(
            container_id=self.container_id,
            dataset_id=dataset_id,
            status=self.state.name,
            target_size_bytes=self._target_size_bytes,
            allocated_bytes=allocated,
            processed_bytes=processed,
            remaining_bytes=self._target_size_bytes - processed,
            chunk_count=self._metrics.chunk_count,
            subchunk_count=self._metrics.subchunk_count,
            metrics=self._metrics,
            checksum_sha256=self._dataset_checksum,
            integrity_verified=self._integrity_verified,
            output_path=self._final_dataset_path,
            cleanup_completed=self.state == ContainerState.DESTROYED,
            error=self._error_message,
            
            configured_cpu_budget_cores=self._budget.cpu_budget_cores,
            detected_cpu_cores=cpu_snap.logical_cores or 0,
            process_cpu_percent=self._metrics.cpu_percent_avg,
            configured_ram_budget_bytes=self._budget.ram_budget_bytes,
            process_ram_bytes=self._metrics.peak_ram_bytes,
            active_workers=self._budget.effective_workers(cpu_snap.logical_cores or 1),
            resource_control_actions=[], # We'd need to extract this from exec_mgr if we kept a ref
        )
