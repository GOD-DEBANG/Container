"""
storage/atomic_writer.py

Atomic file write: write to a temporary sibling file then rename.

Rename is atomic on POSIX. On Windows, Path.replace() provides the
closest approximation (it is not atomic but is safer than truncating
the target in-place). The implementation notes this difference.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


class AtomicWriter:
    """
    Write a file atomically:
      1. Write to a .tmp sibling of the target.
      2. fsync the temporary file.
      3. Replace (rename) the target with the temporary file.

    On POSIX rename() is atomic at the filesystem level.
    On Windows Path.replace() is used; it is NOT kernel-atomic but
    is safer than overwriting in-place.
    """

    @staticmethod
    def write(target: Path, data: bytes) -> None:
        """
        Atomically write data to target.

        Raises OSError if the write or rename fails.
        """
        target.parent.mkdir(parents=True, exist_ok=True)

        tmp_fd, tmp_path_str = tempfile.mkstemp(
            dir=target.parent,
            prefix=f".{target.name}.tmp_",
        )
        tmp_path = Path(tmp_path_str)

        try:
            with os.fdopen(tmp_fd, "wb") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            tmp_path.replace(target)
        except Exception:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise
