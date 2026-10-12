"""
src/pulse

PULSE Server: Immutable pulse event architecture with cell pipelines,
compiled trie routing, state fabric, and Server-Sent Events.
"""

from .core.pulse import Pulse
from .core.pipeline import Pipeline, BaseCell, PulseContext
from .core.router import CompiledRouter
from .config import PulseConfig, config
from .app import PulseASGIApp, create_pulse_app, app

__version__ = "0.1.0"

__all__ = [
    "Pulse",
    "Pipeline",
    "BaseCell",
    "PulseContext",
    "CompiledRouter",
    "PulseConfig",
    "config",
    "PulseASGIApp",
    "create_pulse_app",
    "app",
]
