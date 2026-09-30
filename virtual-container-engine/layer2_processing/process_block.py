"""
layer2_processing/process_block.py

A ProcessBlock is a unit of work: one subchunk routed, read, processed,
and validated. Control metadata is kept separate from actual bytes.
"""

from __future__ import annotations

from dataclasses import dataclass

from models.subchunk_model import SubchunkModel
from models.processing_model import ProcessingResult


@dataclass
class ProcessBlock:
    """
    Encapsulates one processing unit.

    Control metadata (subchunk descriptor, data path) is separated from
    the actual dataset bytes. Bytes are only loaded immediately before
    the processor is called.
    """

    subchunk: SubchunkModel
    data_path: str          # relative path in temporary storage
    worker_id: str = ""     # assigned by WorkerManager

    # Set after completion:
    result: ProcessingResult | None = None

    @property
    def is_complete(self) -> bool:
        return self.result is not None

    @property
    def succeeded(self) -> bool:
        from models.processing_model import ProcessingStatus
        return (
            self.result is not None
            and self.result.status == ProcessingStatus.SUCCESS
        )
