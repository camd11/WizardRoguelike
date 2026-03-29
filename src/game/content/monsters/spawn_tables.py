"""Spawn tables: which monsters appear at which difficulty levels."""
from __future__ import annotations

from typing import Callable

from game.content.monsters.tier1 import TIER1_SPAWNS
from game.content.monsters.tier2 import TIER2_SPAWNS
from game.content.monsters.tier3 import TIER3_SPAWNS
from game.content.monsters.variants import VARIANT_SPAWNS
from game.content.monsters.special import (
    SPECIAL_SPAWNS,
    make_blade_dancer,
    make_blink_fox,
    make_bomb_beetle,
    make_flame_acolyte,
    make_mind_flayer,
    make_plague_rat,
    make_rat_swarm,
)
from game.core.unit import Unit


# Subsets of SPECIAL_SPAWNS by difficulty tier
_SPECIAL_DIFF2 = [make_plague_rat, make_rat_swarm]
_SPECIAL_DIFF3 = [make_flame_acolyte, make_bomb_beetle, make_blade_dancer,
                  make_blink_fox]
_SPECIAL_DIFF4 = [s for s in SPECIAL_SPAWNS if s is not make_mind_flayer]
_SPECIAL_DIFF5 = list(SPECIAL_SPAWNS)


def get_spawn_options(difficulty: int) -> list[Callable[[], Unit]]:
    """Get available monster spawns for a given difficulty level (1-5).

    Difficulty 1:   tier 1 only
    Difficulty 2:   tier 1 + early variants + easy specials (Plague Rat, Rat Swarm)
    Difficulty 3:   tier 1 + all variants + some tier 2 + mid specials
    Difficulty 4:   tier 1 + all variants + tier 2 + some tier 3 + most specials
    Difficulty 5:   tier 1 + all variants + tier 2 + all tier 3 + all specials
    """
    if difficulty <= 1:
        return list(TIER1_SPAWNS)
    elif difficulty == 2:
        return list(TIER1_SPAWNS) + VARIANT_SPAWNS[:3] + _SPECIAL_DIFF2
    elif difficulty == 3:
        return (list(TIER1_SPAWNS) + list(VARIANT_SPAWNS) + TIER2_SPAWNS[:2]
                + _SPECIAL_DIFF3)
    elif difficulty == 4:
        return (list(TIER1_SPAWNS) + list(VARIANT_SPAWNS)
                + list(TIER2_SPAWNS) + TIER3_SPAWNS[:2] + _SPECIAL_DIFF4)
    else:
        return (list(TIER1_SPAWNS) + list(VARIANT_SPAWNS)
                + list(TIER2_SPAWNS) + list(TIER3_SPAWNS) + _SPECIAL_DIFF5)


def get_monster_count(difficulty: int) -> int:
    """How many monsters to spawn on a level."""
    # Level 1: 5, Level 2: 6, Level 3: 8, Level 4: 9, Level 5: 10
    return min(3 + difficulty * 2, 12) if difficulty <= 2 else min(4 + difficulty * 2, 12)
