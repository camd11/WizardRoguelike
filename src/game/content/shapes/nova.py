"""Nova shape — self-centered burst that damages all nearby enemies."""
from __future__ import annotations

from typing import Generator

from game.core.shapes import burst as burst_iter, get_burst_points
from game.core.types import Point


def cast(spell, x: int, y: int) -> Generator[None, None, None]:
    """Explode outward from the caster, hitting all enemies in radius.

    Unlike Burst, Nova is always centered on the caster (x, y are ignored
    in favor of caster position) and does not damage the caster.
    """
    level = spell.level
    caster = spell.caster
    origin = Point(caster.x, caster.y)
    radius = spell.get_stat("radius")
    damage = spell.get_stat("damage")
    damage_type = spell.damage_type

    for stage in burst_iter(level, origin, radius):
        for p in stage:
            if p.x == caster.x and p.y == caster.y:
                continue  # Don't damage self.
            unit = level.get_unit_at(p.x, p.y)
            if unit is not None and unit.team != caster.team:
                level.deal_damage(p.x, p.y, damage, damage_type, spell)
                spell._apply_element_secondary(p.x, p.y)
                spell._apply_modifier_effects(p.x, p.y)
        yield


def get_impacted_tiles(spell, x: int, y: int) -> list[Point]:
    """Return burst tiles centered on the caster."""
    if spell.level is None:
        return [Point(x, y)]
    origin = Point(spell.caster.x, spell.caster.y)
    radius = spell.get_stat("radius")
    return get_burst_points(spell.level, origin, radius)
