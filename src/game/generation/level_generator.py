"""Level generator — produces complete, playable levels."""
from __future__ import annotations

from game.constants import LEVEL_SIZE
from game.core.level import Level
from game.core.rng import GameRNG
from game.core.types import Point
from game.core.unit import Unit
from game.generation.biomes import Biome, get_biome_for_difficulty
from game.generation.populator import place_exit, place_monsters, place_player
from game.generation.room_builders import generate_rooms


class GeneratedLevel:
    """A fully generated level ready to play."""

    def __init__(self, level: Level, player_pos: Point, exit_pos: Point | None,
                 biome: Biome, difficulty: int, monsters: list[Unit]) -> None:
        self.level = level
        self.player_pos = player_pos
        self.exit_pos = exit_pos
        self.biome = biome
        self.difficulty = difficulty
        self.monsters = monsters


def generate_level(difficulty: int, player: Unit, seed: int | None = None,
                   width: int = LEVEL_SIZE, height: int = LEVEL_SIZE) -> GeneratedLevel:
    """Generate a complete level with rooms, monsters, and exits.

    Args:
        difficulty: 1-5, determines monster types and counts
        player: The player unit to place
        seed: RNG seed for deterministic generation
        width: Level width in tiles
        height: Level height in tiles
    """
    rng = GameRNG(seed=seed)

    level = Level(width, height)

    # Select biome
    biome = get_biome_for_difficulty(difficulty, rng)

    # Generate rooms and corridors
    room_count = 4 + difficulty
    rooms = generate_rooms(
        level, rng,
        min_rooms=max(3, room_count - 1),
        max_rooms=room_count + 1,
        min_size=3,
        max_size=min(7, width // 4),
    )

    # Ensure at least one room exists
    if not rooms:
        # Emergency: carve a big room in the center
        cx = width // 4
        cy = height // 4
        rw = width // 2
        rh = height // 2
        from game.constants import TileType
        for x in range(cx, cx + rw):
            for y in range(cy, cy + rh):
                level.set_tile_type(x, y, TileType.FLOOR)
        rooms = [(cx, cy, rw, rh)]

    # Place player in first room
    player_pos = place_player(level, rooms, player)

    # Place exit in last room
    exit_pos = place_exit(level, rooms, rng)

    # Spawn monsters
    monsters = place_monsters(level, rng, difficulty, rooms)

    return GeneratedLevel(
        level=level,
        player_pos=player_pos,
        exit_pos=exit_pos,
        biome=biome,
        difficulty=difficulty,
        monsters=monsters,
    )
