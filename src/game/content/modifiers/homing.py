"""Homing modifier — spell auto-targets nearest enemy."""
from __future__ import annotations

from game.core.types import Point


def modify_stats(spell, stats: dict) -> dict:
    return stats


def apply_effect(spell, level, x: int, y: int) -> None:
    """No post-hit effect — homing modifies targeting, not damage."""
    pass


def retarget(spell, x: int, y: int) -> Point:
    """Find the nearest enemy to the original target location.

    Used by CraftedSpell to adjust the target before casting.
    """
    level = spell.level
    caster = spell.caster
    if not level or not caster:
        return Point(x, y)

    origin = Point(x, y)
    best = None
    best_dist = float("inf")

    for unit in level.units:
        if unit.team == caster.team or not unit.is_alive():
            continue
        pos = Point(unit.x, unit.y)
        dist = origin.distance_to(pos)
        if dist < best_dist:
            # Check if we can actually cast at this target
            caster_pos = Point(caster.x, caster.y)
            effective_range = spell.get_stat("range")
            if caster_pos.distance_to(pos) <= effective_range + 0.5:
                best_dist = dist
                best = pos

    return best if best else Point(x, y)
