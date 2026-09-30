"""
layer2_processing/id_router.py

Validates all three IDs (dataset_id, chunk_id, subchunk_id) and
sequence index before dispatching a subchunk to a processor.

This is the pre-processing validation gate mandated by the spec.
"""

from __future__ import annotations

from dataclasses import dataclass

from models.allocation_model import AllocationManifest
from models.subchunk_model import SubchunkModel


@dataclass
class RouteResult:
    valid: bool
    subchunk: SubchunkModel | None
    data_path: str   # relative path for reading from temp storage
    error: str = ""


class IDRouter:
    """
    Resolves a (chunk_index, subchunk_index) coordinate to a validated
    SubchunkModel and storage path.

    Pre-processing checks (spec §7):
      1. Validate dataset_id.
      2. Validate chunk_id.
      3. Validate subchunk_id.
      4. Validate sequence index.
      5. Resolve the data reference/offset.
    """

    def __init__(self, manifest: AllocationManifest) -> None:
        self._manifest = manifest
        # Build lookup tables for O(1) access
        self._chunks_by_id = {c.chunk_id: c for c in manifest.chunks}
        self._subs_by_id: dict[str, SubchunkModel] = {}
        for subs in manifest.subchunks.values():
            for s in subs:
                self._subs_by_id[s.subchunk_id] = s

    def route(self, subchunk_id: str) -> RouteResult:
        """
        Validate all IDs and return the routing result.
        """
        sub = self._subs_by_id.get(subchunk_id)
        if sub is None:
            return RouteResult(
                valid=False,
                subchunk=None,
                data_path="",
                error=f"subchunk_id not found: {subchunk_id!r}",
            )

        # Validate dataset_id
        if sub.dataset_id != self._manifest.dataset_id:
            return RouteResult(
                valid=False,
                subchunk=None,
                data_path="",
                error=(
                    f"subchunk dataset_id {sub.dataset_id!r} != "
                    f"manifest dataset_id {self._manifest.dataset_id!r}"
                ),
            )

        # Validate chunk_id
        chunk = self._chunks_by_id.get(sub.chunk_id)
        if chunk is None:
            return RouteResult(
                valid=False,
                subchunk=None,
                data_path="",
                error=f"chunk_id {sub.chunk_id!r} not in manifest",
            )

        # Validate subchunk_index against the chunk's subchunk list
        chunk_subs = self._manifest.subchunks.get(chunk.chunk_id, [])
        if sub.subchunk_index >= len(chunk_subs):
            return RouteResult(
                valid=False,
                subchunk=None,
                data_path="",
                error=(
                    f"subchunk_index {sub.subchunk_index} out of range "
                    f"for chunk {chunk.chunk_index} ({len(chunk_subs)} subchunks)"
                ),
            )
        if chunk_subs[sub.subchunk_index].subchunk_id != subchunk_id:
            return RouteResult(
                valid=False,
                subchunk=None,
                data_path="",
                error=f"Sequence mismatch at subchunk_index {sub.subchunk_index}",
            )

        # Resolve storage path
        data_path = (
            f"chunks/{chunk.chunk_index}/subchunks/{sub.subchunk_index}.bin"
        )

        return RouteResult(
            valid=True,
            subchunk=sub,
            data_path=data_path,
        )
