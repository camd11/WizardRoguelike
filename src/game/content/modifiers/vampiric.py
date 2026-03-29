"""Vampiric modifier — heals caster for 25% of damage dealt."""


def modify_stats(spell, stats: dict) -> dict:
    """No stat modification — vampiric is a post-hit effect."""
    return stats


def apply_effect(spell, level, x: int, y: int) -> None:
    """Heal caster for 25% of spell damage (minimum 1)."""
    if spell.caster is None:
        return
    heal_amount = max(1, spell.get_stat("damage") // 4)
    spell.caster.cur_hp = min(spell.caster.cur_hp + heal_amount, spell.caster.max_hp)
