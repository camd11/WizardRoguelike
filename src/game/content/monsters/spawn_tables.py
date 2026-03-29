"""Spawn tables: which monsters appear at which difficulty levels."""
from __future__ import annotations

from typing import Callable

from game.content.monsters.tier1 import TIER1_SPAWNS
from game.content.monsters.tier2 import TIER2_SPAWNS
from game.core.unit import Unit


def get_spawn_options(difficulty: int) -> list[Callable[[], Unit]]:
    """Get available monster spawns for a given difficulty level (1-5).

    Difficulty 1-2: tier 1 only
    Difficulty 3: tier 1 + some tier 2
    Difficulty 4-5: tier 1 + tier 2
    """
    if difficulty <= 2:
        return list(TIER1_SPAWNS)
    elif difficulty == 3:
        return list(TIER1_SPAWNS) + TIER2_SPAWNS[:2]
    else:
        return list(TIER1_SPAWNS) + list(TIER2_SPAWNS)


def get_monster_count(difficulty: int) -> int:
    """How many monsters to spawn on a level."""
    return min(4 + difficulty * 2, 14)
