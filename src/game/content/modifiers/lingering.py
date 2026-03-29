"""Lingering modifier — creates a persistent damage zone at the impact point."""
from __future__ import annotations

from game.constants import Team
from game.core.cloud import create_cloud


def modify_stats(spell, stats: dict) -> dict:
    return stats


def apply_effect(spell, level, x: int, y: int) -> None:
    """Create a lingering cloud zone at the impact point."""
    for mod in spell._modifiers:
        if mod.name == "Lingering" and mod.dot_turns > 0:
            damage = max(1, spell.get_stat("damage") // 3)
            team = spell.caster.team if spell.caster else Team.PLAYER
            create_cloud(
                level, x, y,
                damage=damage,
                damage_type=spell.damage_type,
                source=spell,
                duration=mod.dot_turns,
                team=team,
            )
            break
