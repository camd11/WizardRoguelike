"""Biome definitions — tileset themes + spawn tag requirements."""
from __future__ import annotations

from dataclasses import dataclass, field

from game.constants import Tag, Tags


@dataclass(frozen=True)
class Biome:
    name: str
    floor_sprite: str
    wall_sprite: str
    tags: list[Tag] = field(default_factory=list)
    min_difficulty: int = 1
    max_difficulty: int = 5


BIOMES = [
    Biome("Stone Dungeon", "tiles/floor/stone", "tiles/wall/stone",
          min_difficulty=1, max_difficulty=3),
    Biome("Cavern", "tiles/floor/cavern", "tiles/wall/cavern",
          min_difficulty=1, max_difficulty=4),
    Biome("Dead Woods", "tiles/floor/dead_woods", "tiles/wall/dead_woods",
          tags=[Tags.Undead, Tags.Dark], min_difficulty=2, max_difficulty=5),
    Biome("Flame Pit", "tiles/floor/flesh", "tiles/wall/flesh",
          tags=[Tags.Demon], min_difficulty=3, max_difficulty=5),
    Biome("Frozen Cavern", "tiles/floor/mushroom_green", "tiles/wall/mushroom_green",
          min_difficulty=2, max_difficulty=5),
]


def get_biome_for_difficulty(difficulty: int, rng) -> Biome:
    """Select a random biome appropriate for the difficulty."""
    valid = [b for b in BIOMES if b.min_difficulty <= difficulty <= b.max_difficulty]
    if not valid:
        valid = BIOMES
    return rng.choice(valid)
