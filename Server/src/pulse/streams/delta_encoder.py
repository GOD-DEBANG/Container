"""
src/pulse/streams/delta_encoder.py

Versioned state delta creation and reconstruction.
Emits compact JSON diffs between successive job states.
"""

from __future__ import annotations

from typing import Any, Dict


class DeltaEncoder:
    @staticmethod
    def compute_delta(prev_state: Dict[str, Any], new_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute delta mapping of added/modified keys and deleted keys.
        Format:
          {
            "set": {key: val, ...},
            "del": [key, ...]
          }
        """
        updates: Dict[str, Any] = {}
        deletions: list[str] = []

        for k, v in new_state.items():
            if k not in prev_state or prev_state[k] != v:
                updates[k] = v

        for k in prev_state:
            if k not in new_state:
                deletions.append(k)

        delta: Dict[str, Any] = {}
        if updates:
            delta["set"] = updates
        if deletions:
            delta["del"] = deletions
        return delta

    @staticmethod
    def apply_delta(base_state: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reconstruct state by applying delta on top of base_state.
        """
        result = dict(base_state)
        for k, v in delta.get("set", {}).items():
            result[k] = v
        for k in delta.get("del", []):
            result.pop(k, None)
        return result
