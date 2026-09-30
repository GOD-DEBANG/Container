"""
storage/persistent_storage.py

Permanent output storage for committed datasets.
Survives container destruction.
"""

from __future__ import annotations

from pathlib import Path

from storage.storage_interface import StorageInterface


class PersistentStorage(StorageInterface):
    """
    Committed output storage. Never deleted by container cleanup.

    Lives in data/output/ by default, but is configurable so the
    engine can write datasets to any caller-specified location.
    """

    def __init__(self, root_dir: Path) -> None:
        self._root = root_dir
        self._root.mkdir(parents=True, exist_ok=True)

    def write(self, relative_path: str, data: bytes) -> Path:
        target = self._root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return target

    def read(self, relative_path: str) -> bytes:
        return (self._root / relative_path).read_bytes()

    def exists(self, relative_path: str) -> bool:
        return (self._root / relative_path).exists()

    def delete(self, relative_path: str) -> None:
        path = self._root / relative_path
        if path.exists():
            path.unlink()

    def root(self) -> Path:
        return self._root
