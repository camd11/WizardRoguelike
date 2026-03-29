"""Lingering modifier — creates a persistent damage zone at the impact point."""
from __future__ import annotations

from game.core.buff import Buff


class LingeringZone:
    """A persistent zone on the ground that damages enemies each turn.

    This is tracked on the tile's cloud slot. Each turn it deals damage
    to any enemy standing on it.
    """

    def __init__(self, x: int, y: int, damage: int, damage_type, source, turns: int) -> None:
        self.x = x
        self.y = y
        self.damage = damage
        self.damage_type = damage_type
        self.source = source
        self.turns_left = turns
        self.team = source.caster.team if hasattr(source, 'caster') and source.caster else None

    def advance(self, level) -> bool:
        """Tick the zone. Returns False when expired."""
        unit = level.get_unit_at(self.x, self.y)
        if unit and unit.is_alive():
            if self.team is None or unit.team != self.team:
                level.deal_damage(self.x, self.y, self.damage, self.damage_type, self.source)

        self.turns_left -= 1
        return self.turns_left > 0


def modify_stats(spell, stats: dict) -> dict:
    return stats


def apply_effect(spell, level, x: int, y: int) -> None:
    """Create a lingering zone at the impact point."""
    for mod in spell._modifiers:
        if mod.name == "Lingering" and mod.dot_turns > 0:
            zone = LingeringZone(
                x=x, y=y,
                damage=max(1, spell.get_stat("damage") // 3),
                damage_type=spell.damage_type,
                source=spell,
                turns=mod.dot_turns,
            )
            tile = level.get_tile(x, y)
            if tile:
                tile.cloud = zone
            break
