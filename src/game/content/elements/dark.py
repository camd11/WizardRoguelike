"""Dark element — lifedrain secondary effect."""
from __future__ import annotations


def apply_secondary(spell, level, x: int, y: int) -> None:
    """Heal the caster for 25% of damage dealt."""
    unit = level.get_unit_at(x, y)
    if unit and not unit.is_alive():
        return
    if spell.caster and spell.caster.is_alive():
        # Heal 25% of base damage (approximate)
        heal = max(1, spell.get_stat("damage") // 4)
        actual_heal = min(heal, spell.caster.max_hp - spell.caster.cur_hp)
        if actual_heal > 0:
            spell.caster.cur_hp += actual_heal
