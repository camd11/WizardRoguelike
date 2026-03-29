"""Splitting modifier — spell chains to nearby additional targets."""
from __future__ import annotations

from game.core.types import Point


def modify_stats(spell, stats: dict) -> dict:
    return stats


def apply_effect(spell, level, x: int, y: int) -> None:
    """Chain damage to nearby enemies."""
    for mod in spell._modifiers:
        if mod.name == "Splitting" and mod.chain_targets > 0:
            _chain_to_nearby(spell, level, x, y, mod.chain_targets)
            break


def _chain_to_nearby(spell, level, x: int, y: int, count: int) -> None:
    """Find nearby enemies and deal reduced damage to them."""
    origin = Point(x, y)
    caster = spell.caster
    damage = max(1, spell.get_stat("damage") // 2)  # Chain does half damage
    damage_type = spell.damage_type

    # Find nearby enemies sorted by distance
    candidates = []
    for unit in level.units:
        if unit.team == caster.team or not unit.is_alive():
            continue
        pos = Point(unit.x, unit.y)
        if pos == origin:
            continue  # Don't chain to original target
        dist = origin.distance_to(pos)
        if dist <= 4.5:  # Chain range
            candidates.append((dist, unit))

    candidates.sort(key=lambda x: x[0])

    for _, unit in candidates[:count]:
        level.deal_damage(unit.x, unit.y, damage, damage_type, spell)
