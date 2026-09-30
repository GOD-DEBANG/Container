"""
layer1_hierarchical/dataset_id_manager.py

Generates globally unique, deterministic dataset IDs.

A dataset_id is a UUID-4 combined with a SHA-256 hash of the
configuration parameters, ensuring:
  1. Uniqueness across containers (UUID entropy).
  2. Reproducibility linkage (config hash suffix for audit).
"""

from __future__ import annotations

import hashlib
import uuid


class DatasetIDManager:
    """Creates and validates dataset IDs."""

    @staticmethod
    def generate(
        container_id: str,
        target_size_bytes: int,
        seed: int,
    ) -> str:
        """
        Generate a unique dataset_id.

        Format: <uuid4>-<config_hash_prefix>
        """
        uid = str(uuid.uuid4())
        config_str = f"{container_id}:{target_size_bytes}:{seed}"
        config_hash = hashlib.sha256(config_str.encode()).hexdigest()[:12]
        return f"{uid}-{config_hash}"

    @staticmethod
    def validate(dataset_id: str) -> bool:
        """Return True if the dataset_id has the expected format."""
        parts = dataset_id.split("-")
        # UUID4 has 5 parts (8-4-4-4-12) plus our config hash = 6 parts
        return len(parts) == 6 and all(len(p) > 0 for p in parts)
