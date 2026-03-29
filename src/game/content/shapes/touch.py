"""Touch shape — melee range spell, instant cast."""
from __future__ import annotations

from typing import Generator

from game.core.types import Point


def cast(spell, x: int, y: int) -> Generator[None, None, None]:
    """Melee range attack. Instant, no projectile animation."""
    level = spell.level
    caster = spell.caster
    damage = spell.get_stat("damage")
    damage_type = spell.damage_type

    unit = level.get_unit_at(x, y)
    if unit is not None and unit.team != caster.team:
        level.deal_damage(x, y, damage, damage_type, spell)
        spell._apply_element_secondary(x, y)
        spell._apply_modifier_effects(x, y)
    yield


def get_impacted_tiles(spell, x: int, y: int) -> list[Point]:
    return [Point(x, y)]
