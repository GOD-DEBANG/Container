"""
src/vdc/storage

Storage implementations for the Virtual Container engine.
"""

from .storage_interface import StorageInterface
from .temporary_storage import TemporaryStorage
from .persistent_storage import PersistentStorage

__all__ = [
    "StorageInterface",
    "TemporaryStorage",
    "PersistentStorage",
]
