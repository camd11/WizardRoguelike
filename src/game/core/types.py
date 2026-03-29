"""Core data types used throughout the engine."""
from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from game.constants import Tag


class Point(NamedTuple):
    """An (x, y) position on the grid."""
    x: int
    y: int

    def distance_to(self, other: Point) -> float:
        """Euclidean distance."""
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

    def chebyshev(self, other: Point) -> int:
        """Chebyshev (chess king) distance."""
        return max(abs(self.x - other.x), abs(self.y - other.y))

    def manhattan(self, other: Point) -> int:
        """Manhattan distance."""
        return abs(self.x - other.x) + abs(self.y - other.y)

    def adjacent(self) -> list[Point]:
        """8-directional neighbors."""
        return [
            Point(self.x + dx, self.y + dy)
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
            if (dx, dy) != (0, 0)
        ]


class Color(NamedTuple):
    """RGB color."""
    r: int
    g: int
    b: int


class DamageEvent(NamedTuple):
    """Record of a damage instance."""
    unit: object  # Unit that took damage
    damage: int   # Amount after resistance
    damage_type: Tag
    source: object  # Spell or Buff that caused it
