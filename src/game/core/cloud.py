"""Cloud/zone system — persistent AOE effects on tiles.

Clouds are created by the Lingering modifier and some spells.
They occupy a tile and damage/affect any unit that enters or
stands on them. Clouds advance each turn and expire.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from game.constants import Tag, Tags, Team

if TYPE_CHECKING:
    from game.core.level import Level


class Cloud:
    """A persistent damage zone on a tile."""

    def __init__(self, x: int, y: int, damage: int, damage_type: Tag,
                 source: object, duration: int, team: Team = Team.PLAYER) -> None:
        self.x = x
        self.y = y
        self.damage = damage
        self.damage_type = damage_type
        self.source = source
        self.turns_left = duration
        self.team = team
        self.name = f"{damage_type.name} Zone"
        self.color = damage_type.color

    def advance(self, level: Level) -> bool:
        """Tick the cloud. Deals damage to enemies standing on it. Returns False when expired."""
        unit = level.get_unit_at(self.x, self.y)
        if unit and unit.is_alive() and unit.team != self.team:
            level.deal_damage(self.x, self.y, self.damage, self.damage_type, self.source)

        self.turns_left -= 1
        return self.turns_left > 0

    @property
    def alive(self) -> bool:
        return self.turns_left > 0


def create_cloud(level: Level, x: int, y: int, damage: int, damage_type: Tag,
                 source: object, duration: int, team: Team = Team.PLAYER) -> Cloud | None:
    """Create a cloud on a tile. Returns None if tile already has a cloud."""
    tile = level.get_tile(x, y)
    if tile is None or tile.is_wall:
        return None

    cloud = Cloud(x, y, damage, damage_type, source, duration, team)
    tile.cloud = cloud
    return cloud
