"""Bolt shape — projectile that travels in a line, stops at first target."""
from __future__ import annotations

from typing import Generator

from game.core.shapes import bolt as bolt_iter, get_bolt_points
from game.core.types import Point


def cast(spell, x: int, y: int) -> Generator[None, None, None]:
    """Fire a bolt from caster to target. Deals damage to first unit hit."""
    level = spell.level
    caster = spell.caster
    start = Point(caster.x, caster.y)
    end = Point(x, y)

    damage = spell.get_stat("damage")
    damage_type = spell.damage_type

    for stage in bolt_iter(level, start, end):
        for p in stage:
            unit = level.get_unit_at(p.x, p.y)
            if unit is not None and unit.team != caster.team:
                level.deal_damage(p.x, p.y, damage, damage_type, spell)
                spell._apply_element_secondary(p.x, p.y)
                spell._apply_modifier_effects(p.x, p.y)
                return
        yield


def get_impacted_tiles(spell, x: int, y: int) -> list[Point]:
    if spell.level is None:
        return [Point(x, y)]
    start = Point(spell.caster.x, spell.caster.y)
    return get_bolt_points(spell.level, start, Point(x, y))
