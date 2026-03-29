"""Chain shape — bolt-like projectile that bounces to nearby enemies."""
from __future__ import annotations

import math
from typing import Generator

from game.core.shapes import bolt as bolt_iter
from game.core.types import Point


# Maximum number of bounces after the initial hit.
MAX_BOUNCES = 2
# Each bounce target must be within this many tiles of the previous.
BOUNCE_RADIUS = 3
# Damage multiplier per bounce (applied cumulatively).
BOUNCE_DECAY = 0.8


def cast(spell, x: int, y: int) -> Generator[None, None, None]:
    """Fire a bolt at the target. On hit, chain to up to 2 nearby enemies.

    Each bounce deals 80% of the previous hit's damage.
    """
    level = spell.level
    caster = spell.caster
    start = Point(caster.x, caster.y)
    end = Point(x, y)

    base_damage = spell.get_stat("damage")
    damage_type = spell.damage_type
    current_damage = base_damage

    visited: set[int] = set()  # Track hit unit ids to avoid re-hitting.

    # --- Primary bolt ---
    hit_unit = None
    for stage in bolt_iter(level, start, end):
        for p in stage:
            unit = level.get_unit_at(p.x, p.y)
            if unit is not None and unit.team != caster.team:
                level.deal_damage(p.x, p.y, current_damage, damage_type, spell)
                spell._apply_element_secondary(p.x, p.y)
                spell._apply_modifier_effects(p.x, p.y)
                visited.add(id(unit))
                hit_unit = unit
                break
        if hit_unit is not None:
            break
        yield

    if hit_unit is None:
        return

    # --- Bounces ---
    last_pos = Point(hit_unit.x, hit_unit.y)

    for _bounce in range(MAX_BOUNCES):
        yield  # pause between bounces for animation
        current_damage = int(current_damage * BOUNCE_DECAY)
        if current_damage <= 0:
            break

        # Find nearest unvisited enemy within BOUNCE_RADIUS of last hit.
        best_unit = None
        best_dist = float("inf")
        for unit in level.units:
            if not unit.is_alive():
                continue
            if unit.team == caster.team:
                continue
            if id(unit) in visited:
                continue
            dist = math.sqrt((unit.x - last_pos.x) ** 2 + (unit.y - last_pos.y) ** 2)
            if dist <= BOUNCE_RADIUS + 0.5 and dist < best_dist:
                best_dist = dist
                best_unit = unit

        if best_unit is None:
            break

        visited.add(id(best_unit))
        level.deal_damage(best_unit.x, best_unit.y, current_damage, damage_type, spell)
        spell._apply_element_secondary(best_unit.x, best_unit.y)
        spell._apply_modifier_effects(best_unit.x, best_unit.y)
        last_pos = Point(best_unit.x, best_unit.y)


def get_impacted_tiles(spell, x: int, y: int) -> list[Point]:
    """Return the target tile only; bounce targets are determined dynamically."""
    return [Point(x, y)]
