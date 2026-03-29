"""Orb shape — slow-moving projectile that damages everything in its path.

The orb moves one tile per turn along the bolt path, dealing damage
to any unit it passes through. It persists for range/2 turns.
For the vertical slice, orb acts like a bolt but hits everything
(similar to beam but slower with per-turn movement).
"""
from __future__ import annotations

from typing import Generator

from game.core.shapes import get_line
from game.core.types import Point


def cast(spell, x: int, y: int) -> Generator[None, None, None]:
    """Launch an orb that moves one tile per frame along the path."""
    level = spell.level
    caster = spell.caster
    start = Point(caster.x, caster.y)
    end = Point(x, y)
    damage = spell.get_stat("damage")
    damage_type = spell.damage_type

    path = get_line(start, end)[1:]  # Skip caster position

    for p in path:
        if not level.in_bounds(p.x, p.y):
            return
        if level.tiles[p.x][p.y].is_wall:
            return

        unit = level.get_unit_at(p.x, p.y)
        if unit is not None and unit.team != caster.team:
            level.deal_damage(p.x, p.y, damage, damage_type, spell)
            spell._apply_element_secondary(p.x, p.y)
            spell._apply_modifier_effects(p.x, p.y)
            # Orb continues past units (unlike bolt)
        yield


def get_impacted_tiles(spell, x: int, y: int) -> list[Point]:
    if spell.level is None:
        return [Point(x, y)]
    start = Point(spell.caster.x, spell.caster.y)
    path = get_line(start, Point(x, y))[1:]
    result = []
    for p in path:
        if not spell.level.in_bounds(p.x, p.y):
            break
        if spell.level.tiles[p.x][p.y].is_wall:
            break
        result.append(p)
    return result
