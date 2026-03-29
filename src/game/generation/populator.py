"""Level populator — places monsters, exits, and items on generated levels."""
from __future__ import annotations

from typing import TYPE_CHECKING

from game.constants import TileType
from game.core.types import Point

if TYPE_CHECKING:
    from game.core.level import Level
    from game.core.rng import GameRNG
    from game.core.unit import Unit


def get_floor_tiles(level: Level) -> list[Point]:
    """Get all walkable floor tiles with no unit on them."""
    tiles = []
    for x in range(level.width):
        for y in range(level.height):
            tile = level.tiles[x][y]
            if tile.is_floor and tile.unit is None:
                tiles.append(Point(x, y))
    return tiles


def place_player(level: Level, rooms: list[tuple[int, int, int, int]],
                 player: Unit) -> Point:
    """Place the player in the first room's center."""
    if rooms:
        rx, ry, rw, rh = rooms[0]
        px = rx + rw // 2
        py = ry + rh // 2
    else:
        # Fallback: find any floor tile
        floors = get_floor_tiles(level)
        if floors:
            px, py = floors[0].x, floors[0].y
        else:
            px, py = 1, 1

    level.add_unit(player, px, py)
    return Point(px, py)


def place_exit(level: Level, rooms: list[tuple[int, int, int, int]],
               rng: GameRNG) -> Point | None:
    """Place the level exit in the last room."""
    if not rooms:
        return None

    # Use the last room
    rx, ry, rw, rh = rooms[-1]
    ex = rx + rw // 2
    ey = ry + rh // 2

    tile = level.get_tile(ex, ey)
    if tile and tile.unit is None:
        tile.prop = "EXIT"  # Simple marker; will be a proper Prop later
        return Point(ex, ey)

    return None


def place_monsters(level: Level, rng: GameRNG, difficulty: int,
                   rooms: list[tuple[int, int, int, int]]) -> list[Unit]:
    """Spawn monsters in rooms (excluding the first room where player starts)."""
    from game.content.monsters.spawn_tables import get_monster_count, get_spawn_options

    spawns = get_spawn_options(difficulty)
    count = get_monster_count(difficulty)

    # Get floor tiles NOT in the first room
    player_room = rooms[0] if rooms else (0, 0, 0, 0)
    available = []
    for p in get_floor_tiles(level):
        # Skip player's room
        rx, ry, rw, rh = player_room
        if rx <= p.x < rx + rw and ry <= p.y < ry + rh:
            continue
        available.append(p)

    if not available or not spawns:
        return []

    rng.shuffle(available)
    placed = []

    for i in range(min(count, len(available))):
        spawn_func = rng.choice(spawns)
        monster = spawn_func()
        pos = available[i]
        if level.add_unit(monster, pos.x, pos.y):
            placed.append(monster)

    return placed
