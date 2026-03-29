"""Wall shape — line of 5 damage zones perpendicular to the aim direction."""
from __future__ import annotations

import math
from typing import Generator

from game.constants import Team
from game.core.cloud import create_cloud
from game.core.types import Point

# Number of tiles in the wall.
WALL_LENGTH = 5
# Duration of the cloud zones (turns).
CLOUD_DURATION = 3


def _get_wall_tiles(level, caster_pos: Point, target: Point) -> list[Point]:
    """Compute the 5-tile perpendicular line centered on target."""
    dx = target.x - caster_pos.x
    dy = target.y - caster_pos.y

    # Perpendicular direction. If aim is (dx, dy), perpendicular is (-dy, dx).
    # Normalise to unit steps (rounded to nearest int for grid alignment).
    length = math.sqrt(dx * dx + dy * dy)
    if length == 0:
        # Fallback: horizontal wall if caster == target.
        perp_x, perp_y = 1, 0
    else:
        perp_x = -dy / length
        perp_y = dx / length

    half = WALL_LENGTH // 2  # 2 tiles each side of center
    tiles: list[Point] = []
    for i in range(-half, half + 1):
        px = target.x + round(perp_x * i)
        py = target.y + round(perp_y * i)
        if level.in_bounds(px, py) and not level.tiles[px][py].is_wall:
            tiles.append(Point(px, py))
    return tiles


def cast(spell, x: int, y: int) -> Generator[None, None, None]:
    """Create a wall of 5 damage zones perpendicular to the aim direction."""
    level = spell.level
    caster = spell.caster
    caster_pos = Point(caster.x, caster.y)
    target = Point(x, y)

    damage = spell.get_stat("damage")
    damage_type = spell.damage_type
    team = caster.team if caster else Team.PLAYER

    tiles = _get_wall_tiles(level, caster_pos, target)

    for p in tiles:
        # Immediate damage to enemies on the tile.
        unit = level.get_unit_at(p.x, p.y)
        if unit is not None and unit.team != caster.team:
            level.deal_damage(p.x, p.y, damage, damage_type, spell)
            spell._apply_element_secondary(p.x, p.y)
            spell._apply_modifier_effects(p.x, p.y)

        # Persistent cloud zone.
        cloud_damage = max(1, damage // 3)
        create_cloud(
            level, p.x, p.y,
            damage=cloud_damage,
            damage_type=damage_type,
            source=spell,
            duration=CLOUD_DURATION,
            team=team,
        )

    yield  # single animation frame


def get_impacted_tiles(spell, x: int, y: int) -> list[Point]:
    """Return the 5-tile perpendicular wall line."""
    if spell.level is None:
        return [Point(x, y)]
    caster_pos = Point(spell.caster.x, spell.caster.y)
    return _get_wall_tiles(spell.level, caster_pos, Point(x, y))
