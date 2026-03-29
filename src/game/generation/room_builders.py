"""Room/corridor generation with varied geometry.

Room types:
- Rectangular (standard)
- Circular (arena-style)
- L-shaped
- Pillared hall (large room with wall pillars)
- Cross-shaped
- Vault (pre-made template with guaranteed layout)
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from game.constants import TileType

if TYPE_CHECKING:
    from game.core.level import Level
    from game.core.rng import GameRNG


def generate_rooms(level: Level, rng: GameRNG,
                   min_rooms: int = 4, max_rooms: int = 8,
                   min_size: int = 3, max_size: int = 7) -> list[tuple[int, int, int, int]]:
    """Generate varied rooms and connect them.

    Returns list of (x, y, w, h) bounding boxes for each room.
    """
    # Fill with walls
    for x in range(level.width):
        for y in range(level.height):
            level.set_tile_type(x, y, TileType.WALL)

    rooms = []
    num_rooms = rng.randint(min_rooms, max_rooms)

    # First room is always a standard rectangle (player spawn)
    first = _try_place_rect(level, rng, rooms, min_size, max_size)
    if first:
        rooms.append(first)

    # Remaining rooms use varied types
    for _ in range(num_rooms * 15):
        if len(rooms) >= num_rooms:
            break

        room_type = rng.choice(["rect", "rect", "circular", "l_shape", "cross", "pillared"])
        room = None

        if room_type == "rect":
            room = _try_place_rect(level, rng, rooms, min_size, max_size)
        elif room_type == "circular":
            room = _try_place_circular(level, rng, rooms)
        elif room_type == "l_shape":
            room = _try_place_l_shape(level, rng, rooms)
        elif room_type == "cross":
            room = _try_place_cross(level, rng, rooms)
        elif room_type == "pillared":
            room = _try_place_pillared(level, rng, rooms)

        if room:
            rooms.append(room)

    # Always try to add a vault for interesting encounters
    if len(rooms) >= 3:
        vault = _try_place_vault(level, rng, rooms)
        if vault:
            rooms.append(vault)

    # Connect rooms with corridors
    for i in range(len(rooms) - 1):
        _connect_rooms(level, rooms[i], rooms[i + 1], rng)

    # Add some extra connections for loops (makes levels less linear)
    if len(rooms) >= 4:
        extra = rng.randint(1, max(1, len(rooms) // 3))
        for _ in range(extra):
            a = rng.randint(0, len(rooms) - 1)
            b = rng.randint(0, len(rooms) - 1)
            if a != b:
                _connect_rooms(level, rooms[a], rooms[b], rng)

    return rooms


# ---------------------------------------------------------------------------
# Room type generators
# ---------------------------------------------------------------------------

def _try_place_rect(level: Level, rng: GameRNG, existing: list,
                    min_size: int = 3, max_size: int = 7) -> tuple | None:
    """Standard rectangular room."""
    for _ in range(20):
        w = rng.randint(min_size, max_size)
        h = rng.randint(min_size, max_size)
        x = rng.randint(1, level.width - w - 1)
        y = rng.randint(1, level.height - h - 1)

        if not _overlaps(x, y, w, h, existing):
            _carve_rect(level, x, y, w, h)
            return (x, y, w, h)
    return None


def _try_place_circular(level: Level, rng: GameRNG, existing: list) -> tuple | None:
    """Circular arena room."""
    for _ in range(20):
        radius = rng.randint(2, 4)
        cx = rng.randint(radius + 2, level.width - radius - 2)
        cy = rng.randint(radius + 2, level.height - radius - 2)
        x, y = cx - radius, cy - radius
        w = h = radius * 2 + 1

        if not _overlaps(x, y, w, h, existing):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if math.sqrt(dx * dx + dy * dy) <= radius + 0.5:
                        px, py = cx + dx, cy + dy
                        if level.in_bounds(px, py):
                            level.set_tile_type(px, py, TileType.FLOOR)
            return (x, y, w, h)
    return None


def _try_place_l_shape(level: Level, rng: GameRNG, existing: list) -> tuple | None:
    """L-shaped room (two overlapping rectangles)."""
    for _ in range(20):
        w1 = rng.randint(3, 5)
        h1 = rng.randint(4, 6)
        w2 = rng.randint(3, 5)
        h2 = rng.randint(2, 3)
        total_w = max(w1, w2 + w1 // 2)
        total_h = h1

        x = rng.randint(1, level.width - total_w - 1)
        y = rng.randint(1, level.height - total_h - 1)

        if not _overlaps(x, y, total_w, total_h, existing):
            # Vertical part
            _carve_rect(level, x, y, w1, h1)
            # Horizontal extension at bottom
            _carve_rect(level, x + w1 - 1, y + h1 - h2, w2, h2)
            return (x, y, total_w, total_h)
    return None


def _try_place_cross(level: Level, rng: GameRNG, existing: list) -> tuple | None:
    """Cross/plus-shaped room."""
    for _ in range(20):
        arm = rng.randint(2, 3)
        center = rng.randint(2, 3)
        total = arm * 2 + center

        x = rng.randint(1, level.width - total - 1)
        y = rng.randint(1, level.height - total - 1)

        if not _overlaps(x, y, total, total, existing):
            cx, cy = x + arm, y + arm
            # Horizontal bar
            _carve_rect(level, x, cy, total, center)
            # Vertical bar
            _carve_rect(level, cx, y, center, total)
            return (x, y, total, total)
    return None


def _try_place_pillared(level: Level, rng: GameRNG, existing: list) -> tuple | None:
    """Large room with decorative wall pillars."""
    for _ in range(20):
        w = rng.randint(6, 9)
        h = rng.randint(6, 9)
        x = rng.randint(1, level.width - w - 1)
        y = rng.randint(1, level.height - h - 1)

        if not _overlaps(x, y, w, h, existing):
            # Carve full room
            _carve_rect(level, x, y, w, h)
            # Add pillars (wall tiles inside the room)
            for px in range(x + 2, x + w - 1, 3):
                for py in range(y + 2, y + h - 1, 3):
                    if level.in_bounds(px, py):
                        level.set_tile_type(px, py, TileType.WALL)
            return (x, y, w, h)
    return None


def _try_place_vault(level: Level, rng: GameRNG, existing: list) -> tuple | None:
    """Pre-made vault template — a treasure room with narrow entrance."""
    for _ in range(20):
        w, h = 5, 5
        x = rng.randint(1, level.width - w - 1)
        y = rng.randint(1, level.height - h - 1)

        if not _overlaps(x, y, w, h, existing):
            # Carve the vault interior
            _carve_rect(level, x + 1, y + 1, w - 2, h - 2)
            # Single entrance on a random side
            side = rng.choice(["north", "south", "east", "west"])
            if side == "north":
                level.set_tile_type(x + w // 2, y, TileType.FLOOR)
            elif side == "south":
                level.set_tile_type(x + w // 2, y + h - 1, TileType.FLOOR)
            elif side == "east":
                level.set_tile_type(x + w - 1, y + h // 2, TileType.FLOOR)
            elif side == "west":
                level.set_tile_type(x, y + h // 2, TileType.FLOOR)
            return (x, y, w, h)
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _overlaps(x: int, y: int, w: int, h: int, existing: list) -> bool:
    """Check if a room overlaps with existing rooms (1-tile buffer)."""
    for rx, ry, rw, rh in existing:
        if (x - 1 < rx + rw + 1 and x + w + 1 > rx - 1 and
                y - 1 < ry + rh + 1 and y + h + 1 > ry - 1):
            return True
    return False


def _carve_rect(level: Level, x: int, y: int, w: int, h: int) -> None:
    """Carve a rectangular area of floor tiles."""
    for cx in range(x, x + w):
        for cy in range(y, y + h):
            if level.in_bounds(cx, cy):
                level.set_tile_type(cx, cy, TileType.FLOOR)


def _connect_rooms(level: Level, room_a: tuple, room_b: tuple, rng: GameRNG) -> None:
    """Carve a corridor between two rooms using L-shaped paths."""
    ax = room_a[0] + room_a[2] // 2
    ay = room_a[1] + room_a[3] // 2
    bx = room_b[0] + room_b[2] // 2
    by = room_b[1] + room_b[3] // 2

    if rng.random() < 0.5:
        _carve_h_corridor(level, ax, bx, ay)
        _carve_v_corridor(level, ay, by, bx)
    else:
        _carve_v_corridor(level, ay, by, ax)
        _carve_h_corridor(level, ax, bx, by)


def _carve_h_corridor(level: Level, x1: int, x2: int, y: int) -> None:
    for x in range(min(x1, x2), max(x1, x2) + 1):
        if level.in_bounds(x, y):
            level.set_tile_type(x, y, TileType.FLOOR)


def _carve_v_corridor(level: Level, y1: int, y2: int, x: int) -> None:
    for y in range(min(y1, y2), max(y1, y2) + 1):
        if level.in_bounds(x, y):
            level.set_tile_type(x, y, TileType.FLOOR)
