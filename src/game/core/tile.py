"""Tile class representing a single cell in the level grid."""
from __future__ import annotations

from typing import TYPE_CHECKING

from game.constants import TileType

if TYPE_CHECKING:
    from game.core.unit import Unit


class Tile:
    """A single cell in the level grid."""

    __slots__ = ("x", "y", "tile_type", "unit", "prop", "cloud", "sprite_name")

    def __init__(self, x: int, y: int, tile_type: TileType = TileType.FLOOR) -> None:
        self.x = x
        self.y = y
        self.tile_type = tile_type
        self.unit: Unit | None = None
        self.prop: object | None = None     # Portal, shop, shrine, etc.
        self.cloud: object | None = None    # Persistent AOE zone
        self.sprite_name: str = ""

    @property
    def is_wall(self) -> bool:
        return self.tile_type == TileType.WALL

    @property
    def is_floor(self) -> bool:
        return self.tile_type == TileType.FLOOR

    @property
    def is_chasm(self) -> bool:
        return self.tile_type == TileType.CHASM

    def can_walk(self, flying: bool = False) -> bool:
        """Can a unit stand on this tile?"""
        if self.tile_type == TileType.WALL:
            return False
        if self.tile_type == TileType.CHASM and not flying:
            return False
        return self.unit is None

    def blocks_los(self) -> bool:
        """Does this tile block line of sight?"""
        return self.tile_type == TileType.WALL

    def __repr__(self) -> str:
        return f"Tile({self.x}, {self.y}, {self.tile_type.name})"
