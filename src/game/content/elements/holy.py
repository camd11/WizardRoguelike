"""Holy element — bonus damage to undead/demons, small bonus to all others."""
from __future__ import annotations

from game.constants import Tags


def apply_secondary(spell, level, x: int, y: int) -> None:
    """Deal bonus holy damage. 50% bonus vs Undead/Demon, 20% vs all others."""
    unit = level.get_unit_at(x, y)
    if unit and unit.is_alive() and unit.team != spell.caster.team:
        is_unholy = Tags.Undead in unit.tags or Tags.Demon in unit.tags
        if is_unholy:
            bonus = max(1, spell.get_stat("damage") // 2)
        else:
            bonus = max(1, spell.get_stat("damage") // 5)
        level.deal_damage(x, y, bonus, Tags.Holy, spell)
