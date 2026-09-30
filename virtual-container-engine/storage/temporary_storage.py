"""
storage/temporary_storage.py

Per-container temporary workspace.

Lives inside Python's tempfile.mkdtemp() directory tree.
Destroyed during container cleanup ONLY when explicitly released —
never touches persistent output directories.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from storage.storage_interface import StorageInterface


class TemporaryStorage(StorageInterface):
    """
    Isolated temporary workspace for one container.

    Each container gets its own unique tempdir (via mkdtemp), so no
    two containers share a temporary workspace.
    """

    def __init__(self, container_id: str, base_dir: Path | None = None) -> None:
        self._container_id = container_id
        parent = base_dir or Path(tempfile.gettempdir())
        self._root = Path(
            tempfile.mkdtemp(prefix=f"vce_{container_id[:8]}_", dir=parent)
        )

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

    def destroy(self) -> None:
        """
        Remove the entire temporary workspace.
        Must be called only after persistent output has been committed.
        """
        if self._root.exists():
            shutil.rmtree(self._root, ignore_errors=True)
