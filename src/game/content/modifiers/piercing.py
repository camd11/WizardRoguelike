"""Piercing modifier — reduces target's effective resistance."""
from __future__ import annotations


def modify_stats(spell, stats: dict) -> dict:
    return stats


def apply_effect(spell, level, x: int, y: int) -> None:
    """No post-hit effect — piercing is applied during damage calculation.

    The CraftedSpell's damage method reduces target resistance by pierce_pct
    before calling deal_damage.
    """
    pass
