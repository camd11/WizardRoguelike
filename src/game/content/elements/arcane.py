"""Arcane element — partial resistance piercing."""
from __future__ import annotations


def apply_secondary(spell, level, x: int, y: int) -> None:
    """Arcane's secondary effect is passive — handled during damage calc.

    Arcane spells inherently pierce 25% of resistance. This is applied
    in CraftedSpell's damage calculation, not as a post-hit effect.
    """
    pass
