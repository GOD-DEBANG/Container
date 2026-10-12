"""
src/vdc/storage/storage_interface.py

Abstract storage interface for reading and writing chunk and dataset artifacts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageInterface(ABC):
    @abstractmethod
    def write_bytes(self, relative_path: str, data: bytes) -> str:
        """Write raw bytes to the relative path, returning absolute or canonical path."""
        pass

    @abstractmethod
    def read_bytes(self, relative_path: str) -> bytes:
        """Read all bytes from the given relative path."""
        pass

    @abstractmethod
    def open_stream_reader(self, relative_path: str) -> BinaryIO:
        """Open a streaming binary file reader for bounded memory consumption."""
        pass

    @abstractmethod
    def open_stream_writer(self, relative_path: str) -> BinaryIO:
        """Open a streaming binary file writer."""
        pass

    @abstractmethod
    def exists(self, relative_path: str) -> bool:
        """Check if file exists."""
        pass

    @abstractmethod
    def delete(self, relative_path: str) -> bool:
        """Delete file if it exists."""
        pass

    @abstractmethod
    def get_size(self, relative_path: str) -> int:
        """Get file size in bytes."""
        pass
