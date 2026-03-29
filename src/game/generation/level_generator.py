"""Level generator — produces complete, playable levels.

Uses RW2-style terrain generation: fill → mutate → validate → populate.
NOT standard roguelike rooms+corridors. See terrain.py for the algorithm.
"""
from __future__ import annotations

from game.constants import LEVEL_SIZE, TileType
from game.core.level import Level
from game.core.rng import GameRNG
from game.core.types import Point
from game.core.unit import Unit
from game.generation.biomes import Biome, get_biome_for_difficulty
from game.generation.populator import get_floor_tiles, place_monsters
from game.generation.terrain import generate_terrain


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
    """Generate a complete level using RW2-style terrain generation.

    Pipeline:
    1. Select biome for visual theming
    2. Generate terrain via fill → mutate → validate → connect
    3. Place player at a random floor tile
    4. Place exit at a distant floor tile
    5. Spawn monsters on remaining floor tiles

    Retries up to 10 times with different RNG forks if terrain validation fails.
    """
    rng = GameRNG(seed=seed)

    # Select biome
    biome = get_biome_for_difficulty(difficulty, rng)

    # Generate terrain with retry loop (RW2 retries up to 25 times)
    level = None
    for attempt in range(10):
        level = Level(width, height)
        terrain_rng = rng.fork(f"terrain_{attempt}")

        success = generate_terrain(level, terrain_rng, difficulty)
        if success:
            break
    else:
        # Emergency fallback: carve a big open area
        level = Level(width, height)
        for x in range(level.width):
            for y in range(level.height):
                level.set_tile_type(x, y, TileType.WALL)
        for x in range(3, width - 3):
            for y in range(3, height - 3):
                level.set_tile_type(x, y, TileType.FLOOR)

    # Place player at a random floor tile
    floors = get_floor_tiles(level)
    if not floors:
        # Absolute emergency
        level.set_tile_type(width // 2, height // 2, TileType.FLOOR)
        floors = [Point(width // 2, height // 2)]

    rng.shuffle(floors)
    player_pos = floors[0]
    level.add_unit(player, player_pos.x, player_pos.y)

    # Place exit at the floor tile farthest from the player (RW2 uses wall spawn points)
    exit_pos = _find_distant_exit(level, player_pos, floors, rng)

    # Place monsters (using populator, which handles lair spawning too)
    # Create dummy room list from floor regions for populator compatibility
    dummy_rooms = [(player_pos.x - 1, player_pos.y - 1, 3, 3)]
    monsters = place_monsters(level, rng, difficulty, dummy_rooms)

    return GeneratedLevel(
        level=level,
        player_pos=player_pos,
        exit_pos=exit_pos,
        biome=biome,
        difficulty=difficulty,
        monsters=monsters,
    )


def _find_distant_exit(level: Level, player_pos: Point,
                       floors: list[Point], rng: GameRNG) -> Point | None:
    """Place exit at a floor tile far from the player.

    RW2 places exits in walls (converting them to floor), but for simplicity
    we just pick a distant floor tile.
    """
    if len(floors) < 5:
        return None

    # Sort by distance from player (descending) and pick from top 10%
    sorted_floors = sorted(
        floors,
        key=lambda p: p.distance_to(player_pos),
        reverse=True,
    )

    # Pick from the farthest 10% of tiles
    candidates = sorted_floors[:max(3, len(sorted_floors) // 10)]
    exit_point = rng.choice(candidates)

    tile = level.get_tile(exit_point.x, exit_point.y)
    if tile and tile.unit is None:
        tile.prop = "EXIT"
        return exit_point

    # Fallback: just use the farthest tile
    for p in sorted_floors:
        tile = level.get_tile(p.x, p.y)
        if tile and tile.unit is None:
            tile.prop = "EXIT"
            return p

    return None
