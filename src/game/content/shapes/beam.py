"""Beam shape — piercing ray that passes through all units."""
from __future__ import annotations

from typing import Generator

from game.core.shapes import beam as beam_iter, get_beam_points
from game.core.types import Point


def cast(spell, x: int, y: int) -> Generator[None, None, None]:
    """Fire a beam from caster to target. Hits everything in the line."""
    level = spell.level
    caster = spell.caster
    start = Point(caster.x, caster.y)
    end = Point(x, y)
    damage = spell.get_stat("damage")
    damage_type = spell.damage_type

    for stage in beam_iter(level, start, end):
        for p in stage:
            unit = level.get_unit_at(p.x, p.y)
            if unit is not None and unit.team != caster.team:
                level.deal_damage(p.x, p.y, damage, damage_type, spell)
                spell._apply_element_secondary(p.x, p.y)
                spell._apply_modifier_effects(p.x, p.y)
        yield


def get_impacted_tiles(spell, x: int, y: int) -> list[Point]:
    if spell.level is None:
        return [Point(x, y)]
    start = Point(spell.caster.x, spell.caster.y)
    return get_beam_points(spell.level, start, Point(x, y))
