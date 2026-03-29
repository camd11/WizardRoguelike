"""SP cost calculation for crafted spells."""
from __future__ import annotations

from game.crafting.components import Element, Modifier, Shape


TIER_MULTIPLIERS = {
    1: 1.0,
    2: 1.5,
    3: 2.5,
}


def calculate_spell_cost(element: Element, shape: Shape,
                         modifiers: list[Modifier] | None = None) -> int:
    """Calculate the total SP cost for crafting a spell.

    Formula:
        base = element.sp_cost + shape.sp_cost + sum(mod.sp_cost)
        tier_mult = max tier multiplier across all components
        total = ceil(base * tier_mult)

    Components are purchased once — this returns the cost of the components
    themselves, not per-craft. Crafting from owned components is free.
    """
    mods = modifiers or []

    base = element.sp_cost + shape.sp_cost + sum(m.sp_cost for m in mods)

    max_tier = max(
        [element.tier, shape.tier] + [m.tier for m in mods],
        default=1,
    )

    tier_mult = TIER_MULTIPLIERS.get(max_tier, 1.0)
    import math
    return math.ceil(base * tier_mult)
