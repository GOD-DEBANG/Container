"""
src/pulse/core/pipeline.py

Cell-based processing pipeline.
Executes an ordered sequence of transformations with explicit typed contracts.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

from .pulse import Pulse
from .errors import PulseError

logger = logging.getLogger(__name__)


@dataclass
class PulseContext:
    incoming_pulse: Pulse
    current_pulse: Pulse
    state: Dict[str, Any] = field(default_factory=dict)
    response_pulse: Optional[Pulse] = None
    aborted: bool = False
    error: Optional[PulseError] = None


class BaseCell(ABC):
    """
    Independently testable transformation cell with explicit contracts.
    """
    name: str = "BaseCell"
    input_contract: Type[Any] = Pulse
    output_contract: Type[Any] = Pulse

    @abstractmethod
    async def process(self, context: PulseContext) -> PulseContext:
        """
        Execute transformation on context.
        Must handle its errors or raise a PulseError.
        """
        pass


class Pipeline:
    def __init__(self, name: str, cells: Optional[List[BaseCell]] = None) -> None:
        self.name = name
        self.cells: List[BaseCell] = cells or []

    def add_cell(self, cell: BaseCell) -> Pipeline:
        self.cells.append(cell)
        return self

    async def execute(self, initial_pulse: Pulse, state: Optional[Dict[str, Any]] = None) -> PulseContext:
        context = PulseContext(
            incoming_pulse=initial_pulse,
            current_pulse=initial_pulse,
            state=state or {},
        )

        for cell in self.cells:
            if context.aborted or context.error is not None:
                break
            try:
                context = await cell.process(context)
            except PulseError as pe:
                context.error = pe
                context.aborted = True
                break
            except Exception as exc:
                logger.exception("Unexpected error in cell %s: %s", cell.name, exc)
                context.error = PulseError(f"Cell execution failed in {cell.name}: {str(exc)}")
                context.aborted = True
                break

        return context
