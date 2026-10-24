"""
src/vdc/storage/temporary_storage.py

Container-scoped temporary storage for intermediate chunk and subchunk artifacts.
Designed to be completely wiped on container cleanup.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import BinaryIO

from .storage_interface import StorageInterface


class TemporaryStorage(StorageInterface):
    def __init__(self, base_dir: Path | str) -> None:
        self.root_path = Path(base_dir).resolve()
        self.root_path.mkdir(parents=True, exist_ok=True)

    def _resolve(self, relative_path: str) -> Path:
        resolved = (self.root_path / relative_path).resolve()
        if not str(resolved).startswith(str(self.root_path)):
            raise ValueError(f"Path traversal detected: {relative_path}")
        return resolved

    def write_bytes(self, relative_path: str, data: bytes) -> str:
        dest = self._resolve(relative_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Write via atomic temp file
        temp_dest = dest.with_suffix(dest.suffix + ".tmp")
        with open(temp_dest, "wb") as f:
            f.write(data)
        temp_dest.replace(dest)
        return str(dest)

    def read_bytes(self, relative_path: str) -> bytes:
        dest = self._resolve(relative_path)
        with open(dest, "rb") as f:
            return f.read()

    def open_stream_reader(self, relative_path: str) -> BinaryIO:
        dest = self._resolve(relative_path)
        return open(dest, "rb")

    def open_stream_writer(self, relative_path: str) -> BinaryIO:
        dest = self._resolve(relative_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        return open(dest, "wb")

    def exists(self, relative_path: str) -> bool:
        dest = self._resolve(relative_path)
        return dest.is_file()

    def delete(self, relative_path: str) -> bool:
        dest = self._resolve(relative_path)
        if dest.exists():
            if dest.is_dir():
                shutil.rmtree(dest)
            else:
                dest.unlink()
            return True
        return False

    def get_size(self, relative_path: str) -> int:
        dest = self._resolve(relative_path)
        return dest.stat().st_size

    def wipe_all(self) -> None:
        """Purge the entire temporary workspace."""
        if self.root_path.exists():
            shutil.rmtree(self.root_path, ignore_errors=True)
