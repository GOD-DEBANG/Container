"""
storage/storage_interface.py

Abstract interface for all storage backends used by the engine.
Implementations: TemporaryStorage (container workspace) and
PersistentStorage (committed output).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class StorageInterface(ABC):
    """
    Abstract storage backend interface.

    All read/write operations go through this interface so the
    storage backend is replaceable via dependency injection.
    """

    @abstractmethod
    def write(self, relative_path: str, data: bytes) -> Path:
        """Write data to a path relative to this storage root."""

    @abstractmethod
    def read(self, relative_path: str) -> bytes:
        """Read data from a path relative to this storage root."""

    @abstractmethod
    def exists(self, relative_path: str) -> bool:
        """Check whether a path exists in this storage root."""

    @abstractmethod
    def delete(self, relative_path: str) -> None:
        """Delete a file from this storage root."""

    @abstractmethod
    def root(self) -> Path:
        """Return the absolute root path of this storage backend."""
