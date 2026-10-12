"""
src/pulse/core/registry.py

Cell registry and flow validator.
Enforces cell contract compatibility and supports controlled prewarming / lazy loading.
"""

from __future__ import annotations

from typing import Callable, Dict, List

from .pipeline import BaseCell
from .errors import ValidationError


class CellRegistry:
    """
    Registry for Cell definitions with contract verification.
    """
    def __init__(self) -> None:
        self._cell_factories: Dict[str, Callable[[], BaseCell]] = {}
        self._instantiated_cells: Dict[str, BaseCell] = {}
        self._prewarmed: set[str] = set()

    def register(self, name: str, factory: Callable[[], BaseCell], prewarm: bool = False) -> None:
        """Register a cell factory function."""
        self._cell_factories[name] = factory
        if prewarm:
            self._instantiated_cells[name] = factory()
            self._prewarmed.add(name)

    def get_cell(self, name: str) -> BaseCell:
        """Obtain a cell instance, lazily instantiating if necessary."""
        if name not in self._instantiated_cells:
            if name not in self._cell_factories:
                raise KeyError(f"Cell '{name}' is not registered in CellRegistry")
            self._instantiated_cells[name] = self._cell_factories[name]()
        return self._instantiated_cells[name]

    def is_instantiated(self, name: str) -> bool:
        return name in self._instantiated_cells

    def prewarm_all(self, names: List[str]) -> None:
        for n in names:
            self.get_cell(n)

    @staticmethod
    def validate_flow(cells: List[BaseCell]) -> bool:
        """
        Validate input/output contracts of an ordered sequence of cells.
        Raises ValidationError if an incompatible interface sequence is detected.
        """
        for i in range(len(cells) - 1):
            curr_cell = cells[i]
            next_cell = cells[i + 1]
            if not issubclass(next_cell.input_contract, curr_cell.output_contract):
                raise ValidationError(
                    f"Flow contract incompatibility: Cell '{curr_cell.name}' outputs "
                    f"{curr_cell.output_contract.__name__}, but Cell '{next_cell.name}' "
                    f"requires input of type {next_cell.input_contract.__name__}"
                )
        return True
