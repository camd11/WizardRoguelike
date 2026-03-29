"""Volatile modifier — target explodes on death, dealing AOE damage."""
from __future__ import annotations

from game.core.events import EventOnDeath
from game.core.shapes import get_burst_points
from game.core.types import Point


def modify_stats(spell, stats: dict) -> dict:
    return stats


def apply_effect(spell, level, x: int, y: int) -> None:
    """Subscribe a death listener on the target that triggers an explosion."""
    unit = level.get_unit_at(x, y)
    if unit is None or not unit.is_alive():
        return

    for mod in spell._modifiers:
        if mod.name == "Volatile" and mod.volatile_radius > 0:
            _attach_volatile(spell, level, unit, mod.volatile_radius)
            break


def _attach_volatile(spell, level, target_unit, radius: int) -> None:
    """Attach a death trigger that causes an explosion."""
    caster_team = spell.caster.team if spell.caster else None
    damage = max(1, spell.get_stat("damage") // 2)
    damage_type = spell.damage_type

    def on_death(event):
        origin = Point(target_unit.x, target_unit.y)
        points = get_burst_points(level, origin, radius, ignore_walls=False)
        for p in points:
            other = level.get_unit_at(p.x, p.y)
            if other and other.is_alive() and other is not target_unit:
                if caster_team is None or other.team != caster_team:
                    level.deal_damage(p.x, p.y, damage, damage_type, spell)

    level.event_handler.subscribe(EventOnDeath, on_death, entity=target_unit)
