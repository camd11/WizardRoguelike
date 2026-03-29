"""Holy element — bonus damage to undead/demons."""
from __future__ import annotations

from game.constants import Tags


def apply_secondary(spell, level, x: int, y: int) -> None:
    """Deal 50% bonus damage to Undead and Demon tagged units."""
    unit = level.get_unit_at(x, y)
    if unit and unit.is_alive() and unit.team != spell.caster.team:
        is_unholy = Tags.Undead in unit.tags or Tags.Demon in unit.tags
        if is_unholy:
            bonus = max(1, spell.get_stat("damage") // 2)
            level.deal_damage(x, y, bonus, Tags.Holy, spell)
