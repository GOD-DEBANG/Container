"""
services/processing_service.py

Service for discovering and registering available processors.
"""

from __future__ import annotations

from typing import Type

from layer2_processing.processor import Processor, BytePreservingProcessor


class ProcessingService:
    """Registry for available processors."""

    def __init__(self) -> None:
        self._processors: dict[str, Type[Processor]] = {
            "byte_preserving": BytePreservingProcessor,
        }

    def get_processor(self, name: str) -> Type[Processor]:
        """Get a processor by name."""
        if name not in self._processors:
            raise ValueError(f"Unknown processor: {name}")
        return self._processors[name]

    def register_processor(self, name: str, processor_cls: Type[Processor]) -> None:
        """Register a new processor type."""
        self._processors[name] = processor_cls
