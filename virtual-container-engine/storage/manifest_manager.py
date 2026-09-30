"""
storage/manifest_manager.py

Saves and loads AllocationManifests as JSON.
Manifests are stored in data/manifests/.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.allocation_model import AllocationManifest
from models.chunk_model import ChunkModel, ChunkStatus
from models.subchunk_model import SubchunkModel, SubchunkStatus


class ManifestManager:
    """Serialises and deserialises AllocationManifests to JSON."""

    def __init__(self, manifest_dir: Path) -> None:
        self._dir = manifest_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, manifest: AllocationManifest) -> Path:
        """Write manifest to disk and return the path."""
        path = self._dir / f"{manifest.dataset_id}.manifest.json"
        data = self._manifest_to_dict(manifest)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        manifest.manifest_path = path
        return path

    def load(self, dataset_id: str) -> AllocationManifest:
        """Load a manifest from disk by dataset_id."""
        path = self._dir / f"{dataset_id}.manifest.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return self._dict_to_manifest(data)

    # ------------------------------------------------------------------ #
    # Serialisation helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _manifest_to_dict(m: AllocationManifest) -> dict[str, Any]:
        chunks = []
        for c in m.chunks:
            subs = []
            for s in m.subchunks.get(c.chunk_id, []):
                subs.append({
                    "subchunk_id": s.subchunk_id,
                    "chunk_id": s.chunk_id,
                    "dataset_id": s.dataset_id,
                    "subchunk_index": s.subchunk_index,
                    "byte_offset": s.byte_offset,
                    "byte_length": s.byte_length,
                    "checksum_sha256": s.checksum_sha256,
                    "status": s.status.name,
                })
            chunks.append({
                "chunk_id": c.chunk_id,
                "dataset_id": c.dataset_id,
                "chunk_index": c.chunk_index,
                "byte_offset": c.byte_offset,
                "byte_length": c.byte_length,
                "checksum_sha256": c.checksum_sha256,
                "status": c.status.name,
                "subchunks": subs,
            })
        return {
            "dataset_id": m.dataset_id,
            "container_id": m.container_id,
            "dataset_total_bytes": m.dataset_total_bytes,
            "chunks": chunks,
        }

    @staticmethod
    def _dict_to_manifest(d: dict[str, Any]) -> AllocationManifest:
        chunks = []
        subchunks: dict[str, list[SubchunkModel]] = {}
        for cd in d["chunks"]:
            c = ChunkModel(
                chunk_id=cd["chunk_id"],
                dataset_id=cd["dataset_id"],
                chunk_index=cd["chunk_index"],
                byte_offset=cd["byte_offset"],
                byte_length=cd["byte_length"],
                checksum_sha256=cd.get("checksum_sha256", ""),
                status=ChunkStatus[cd.get("status", "PENDING")],
            )
            chunks.append(c)
            subs = []
            for sd in cd.get("subchunks", []):
                s = SubchunkModel(
                    subchunk_id=sd["subchunk_id"],
                    chunk_id=sd["chunk_id"],
                    dataset_id=sd["dataset_id"],
                    subchunk_index=sd["subchunk_index"],
                    byte_offset=sd["byte_offset"],
                    byte_length=sd["byte_length"],
                    checksum_sha256=sd.get("checksum_sha256", ""),
                    status=SubchunkStatus[sd.get("status", "PENDING")],
                )
                subs.append(s)
            subchunks[c.chunk_id] = subs
        return AllocationManifest(
            dataset_id=d["dataset_id"],
            container_id=d["container_id"],
            dataset_total_bytes=d["dataset_total_bytes"],
            chunks=chunks,
            subchunks=subchunks,
        )
