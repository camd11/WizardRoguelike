"""Room/corridor generation algorithms for procedural levels."""
from __future__ import annotations

from typing import TYPE_CHECKING

from game.constants import LEVEL_SIZE, TileType

if TYPE_CHECKING:
    from game.core.level import Level
    from game.core.rng import GameRNG


def generate_rooms(level: Level, rng: GameRNG,
                   min_rooms: int = 4, max_rooms: int = 8,
                   min_size: int = 3, max_size: int = 7) -> list[tuple[int, int, int, int]]:
    """Generate random non-overlapping rooms.

    Returns list of (x, y, w, h) tuples.
    Starts by filling everything with walls, then carves rooms + corridors.
    """
    # Fill with walls
    for x in range(level.width):
        for y in range(level.height):
            level.set_tile_type(x, y, TileType.WALL)

    rooms = []
    num_rooms = rng.randint(min_rooms, max_rooms)

    for _ in range(num_rooms * 10):  # Max attempts
        if len(rooms) >= num_rooms:
            break

        w = rng.randint(min_size, max_size)
        h = rng.randint(min_size, max_size)
        x = rng.randint(1, level.width - w - 1)
        y = rng.randint(1, level.height - h - 1)

        # Check overlap with existing rooms (1-tile buffer)
        overlap = False
        for rx, ry, rw, rh in rooms:
            if (x - 1 < rx + rw + 1 and x + w + 1 > rx - 1 and
                    y - 1 < ry + rh + 1 and y + h + 1 > ry - 1):
                overlap = True
                break

        if not overlap:
            rooms.append((x, y, w, h))
            # Carve room
            for cx in range(x, x + w):
                for cy in range(y, y + h):
                    level.set_tile_type(cx, cy, TileType.FLOOR)

    # Connect rooms with corridors
    for i in range(len(rooms) - 1):
        _connect_rooms(level, rooms[i], rooms[i + 1], rng)

    return rooms


def _connect_rooms(level: Level, room_a: tuple, room_b: tuple, rng: GameRNG) -> None:
    """Carve a corridor between two rooms using L-shaped paths."""
    # Center of each room
    ax = room_a[0] + room_a[2] // 2
    ay = room_a[1] + room_a[3] // 2
    bx = room_b[0] + room_b[2] // 2
    by = room_b[1] + room_b[3] // 2

    # Randomly choose horizontal-first or vertical-first
    if rng.random() < 0.5:
        _carve_h_corridor(level, ax, bx, ay)
        _carve_v_corridor(level, ay, by, bx)
    else:
        _carve_v_corridor(level, ay, by, ax)
        _carve_h_corridor(level, ax, bx, by)


def _carve_h_corridor(level: Level, x1: int, x2: int, y: int) -> None:
    """Carve a horizontal corridor."""
    for x in range(min(x1, x2), max(x1, x2) + 1):
        if level.in_bounds(x, y):
            level.set_tile_type(x, y, TileType.FLOOR)


def _carve_v_corridor(level: Level, y1: int, y2: int, x: int) -> None:
    """Carve a vertical corridor."""
    for y in range(min(y1, y2), max(y1, y2) + 1):
        if level.in_bounds(x, y):
            level.set_tile_type(x, y, TileType.FLOOR)
