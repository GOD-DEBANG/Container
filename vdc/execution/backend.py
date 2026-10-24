"""
src/vdc/execution/backend.py

Defines execution backends:
  - INLINE: execute bounded job within current serverless invocation.
  - DURABLE_WORKER: submit job to a separately deployed durable worker backend.
  - LOCAL: run directly from the command line.
"""

from __future__ import annotations

from enum import Enum


class ExecutionBackend(str, Enum):
    INLINE = "INLINE"
    DURABLE_WORKER = "DURABLE_WORKER"
    LOCAL = "LOCAL"
