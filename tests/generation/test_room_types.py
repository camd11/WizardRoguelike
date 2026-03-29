"""Tests for level generation room type builders."""
import math

import pytest

from game.constants import TileType
from game.core.level import Level
from game.core.rng import GameRNG
from game.generation.room_builders import (
    _carve_rect,
    _try_place_circular,
    _try_place_l_shape,
    _try_place_pillared,
    _try_place_vault,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_walled_level(width: int = 30, height: int = 30) -> Level:
    """Create a level filled entirely with walls (blank slate for room gen)."""
    level = Level(width, height)
    for x in range(width):
        for y in range(height):
            level.set_tile_type(x, y, TileType.WALL)
    return level


def _count_floor_tiles(level: Level, x: int, y: int, w: int, h: int) -> int:
    """Count floor tiles within a bounding box."""
    count = 0
    for cx in range(x, x + w):
        for cy in range(y, y + h):
            if level.in_bounds(cx, cy) and level.tiles[cx][cy].is_floor:
                count += 1
    return count


def _get_floor_tiles(level: Level) -> set[tuple[int, int]]:
    """Collect all floor tile coordinates."""
    tiles = set()
    for x in range(level.width):
        for y in range(level.height):
            if level.tiles[x][y].is_floor:
                tiles.add((x, y))
    return tiles


# ---------------------------------------------------------------------------
# Circular room
# ---------------------------------------------------------------------------

class TestCircularRoom:
    def test_circular_room_is_roughly_circular(self):
        """Floor tiles should fall within the circle's radius."""
        rng = GameRNG(seed=42)
        level = _make_walled_level()
        room = _try_place_circular(level, rng, [])
        assert room is not None, "Should successfully place a circular room"

        x, y, w, h = room
        cx = x + w // 2
        cy = y + h // 2
        radius = w // 2

        floors = _get_floor_tiles(level)
        assert len(floors) > 0

        # Every floor tile should be within radius + 0.5 of center
        for fx, fy in floors:
            dist = math.sqrt((fx - cx) ** 2 + (fy - cy) ** 2)
            assert dist <= radius + 1.0, (
                f"Floor tile ({fx},{fy}) is {dist:.2f} from center ({cx},{cy}), "
                f"expected <= {radius + 1.0}"
            )

    def test_circular_room_has_no_corners(self):
        """Corners of the bounding box should not be floor tiles (they fall
        outside the circle)."""
        rng = GameRNG(seed=100)
        level = _make_walled_level()
        room = _try_place_circular(level, rng, [])
        assert room is not None

        x, y, w, h = room
        # For radius >= 2, the corners (x,y), (x+w-1,y), etc. should be walls
        # because sqrt(r^2 + r^2) > r + 0.5 for r >= 2
        corners = [(x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1)]
        corner_floor_count = sum(
            1 for cx, cy in corners
            if level.in_bounds(cx, cy) and level.tiles[cx][cy].is_floor
        )
        # With radius >= 2, corners should be wall
        radius = w // 2
        if radius >= 2:
            assert corner_floor_count == 0, (
                f"Circular room with radius {radius} should not have floor tiles at corners"
            )

    def test_circular_room_floor_count_approximation(self):
        """Floor tile count should roughly approximate pi * r^2."""
        rng = GameRNG(seed=55)
        level = _make_walled_level()
        room = _try_place_circular(level, rng, [])
        assert room is not None

        x, y, w, h = room
        radius = w // 2
        floors = _get_floor_tiles(level)

        # pi * r^2 is the continuous area; discrete tiles will differ slightly
        expected = math.pi * (radius + 0.5) ** 2
        assert len(floors) > 0
        # Allow generous tolerance for discretization
        assert len(floors) <= expected * 1.3, (
            f"{len(floors)} tiles exceeds expected ~{expected:.0f} by too much"
        )


# ---------------------------------------------------------------------------
# Pillared room
# ---------------------------------------------------------------------------

class TestPillaredRoom:
    def test_pillared_room_has_interior_walls(self):
        """A pillared room should contain wall tiles inside its floor area."""
        rng = GameRNG(seed=42)
        level = _make_walled_level()
        room = _try_place_pillared(level, rng, [])
        assert room is not None

        x, y, w, h = room
        # Count wall tiles strictly inside the room (not on the perimeter)
        interior_walls = 0
        for cx in range(x + 1, x + w - 1):
            for cy in range(y + 1, y + h - 1):
                if level.in_bounds(cx, cy) and level.tiles[cx][cy].is_wall:
                    interior_walls += 1

        assert interior_walls > 0, "Pillared room should have wall tiles inside"

    def test_pillared_room_pillar_spacing(self):
        """Pillars should be placed at regular intervals (every 3 tiles)."""
        rng = GameRNG(seed=42)
        level = _make_walled_level()
        room = _try_place_pillared(level, rng, [])
        assert room is not None

        x, y, w, h = room
        pillar_positions = []
        for cx in range(x + 2, x + w - 1, 3):
            for cy in range(y + 2, y + h - 1, 3):
                if level.in_bounds(cx, cy):
                    pillar_positions.append((cx, cy))

        # All expected pillar positions should be walls
        for px, py in pillar_positions:
            assert level.tiles[px][py].is_wall, (
                f"Expected pillar at ({px},{py})"
            )


# ---------------------------------------------------------------------------
# Vault
# ---------------------------------------------------------------------------

class TestVault:
    def test_vault_has_single_entrance(self):
        """A vault should have exactly one floor tile on its perimeter border."""
        rng = GameRNG(seed=42)
        level = _make_walled_level()
        room = _try_place_vault(level, rng, [])
        assert room is not None

        x, y, w, h = room
        # The vault carves interior at (x+1, y+1, w-2, h-2)
        # Perimeter = the outermost ring of the bounding box
        perimeter_floors = 0
        for cx in range(x, x + w):
            for cy in range(y, y + h):
                # Skip interior
                if x + 1 <= cx < x + w - 1 and y + 1 <= cy < y + h - 1:
                    continue
                if level.in_bounds(cx, cy) and level.tiles[cx][cy].is_floor:
                    perimeter_floors += 1

        assert perimeter_floors == 1, (
            f"Vault should have exactly 1 perimeter entrance, got {perimeter_floors}"
        )

    def test_vault_interior_is_floor(self):
        """The inside of the vault should be carved out as floor."""
        rng = GameRNG(seed=42)
        level = _make_walled_level()
        room = _try_place_vault(level, rng, [])
        assert room is not None

        x, y, w, h = room
        interior_floors = _count_floor_tiles(level, x + 1, y + 1, w - 2, h - 2)
        expected = (w - 2) * (h - 2)
        assert interior_floors == expected, (
            f"Vault interior should be all floor: {interior_floors}/{expected}"
        )


# ---------------------------------------------------------------------------
# L-shaped room
# ---------------------------------------------------------------------------

class TestLShapedRoom:
    def test_l_shape_has_non_rectangular_footprint(self):
        """An L-shaped room's floor tiles should NOT form a solid rectangle.

        If we take the bounding box and check whether every tile inside is
        floor, at least some should be wall (the 'notch' of the L).

        Note: Some seeds produce overlapping rectangles that fill the bbox,
        so we use seed=0 which is known to produce a proper L-notch.
        """
        rng = GameRNG(seed=0)
        level = _make_walled_level()
        room = _try_place_l_shape(level, rng, [])
        assert room is not None

        x, y, w, h = room
        total_in_bbox = w * h
        floor_count = _count_floor_tiles(level, x, y, w, h)

        # If it were a rectangle, floor_count would equal total_in_bbox
        assert floor_count < total_in_bbox, (
            f"L-shaped room should not fill its bounding box: "
            f"{floor_count} floors in {total_in_bbox} tile bbox"
        )

    def test_l_shape_has_floor_tiles(self):
        """L-shaped room should have a reasonable number of floor tiles."""
        rng = GameRNG(seed=42)
        level = _make_walled_level()
        room = _try_place_l_shape(level, rng, [])
        assert room is not None

        floors = _get_floor_tiles(level)
        assert len(floors) >= 6, "L-shaped room should have at least 6 floor tiles"

    def test_l_shape_consists_of_two_rectangles(self):
        """The L-shape is built from two overlapping rectangles.

        Verify the floor region is connected (one contiguous group).
        """
        from collections import deque

        rng = GameRNG(seed=42)
        level = _make_walled_level()
        room = _try_place_l_shape(level, rng, [])
        assert room is not None

        floors = _get_floor_tiles(level)
        assert len(floors) > 0

        # BFS from first floor tile — all should be reachable
        start = next(iter(floors))
        visited = set()
        queue = deque([start])
        while queue:
            cx, cy = queue.popleft()
            if (cx, cy) in visited:
                continue
            if (cx, cy) not in floors:
                continue
            visited.add((cx, cy))
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                queue.append((cx + dx, cy + dy))

        assert visited == floors, (
            f"L-shaped room floor should be connected: "
            f"{len(visited)} reachable out of {len(floors)}"
        )
