"""Tests for Level pathfinding and FOV."""
import pytest

from game.constants import TileType
from game.core.level import Level
from game.core.types import Point


class TestPathfinding:
    def test_straight_line_path(self):
        level = Level(9, 9)
        path = level.find_path(0, 4, 8, 4)
        assert path[0] == (0, 4)
        assert path[-1] == (8, 4)
        assert len(path) == 9

    def test_path_around_wall(self):
        level = Level(9, 9)
        # Wall blocking direct path
        for y in range(0, 8):
            level.set_tile_type(4, y, TileType.WALL)
        path = level.find_path(2, 4, 6, 4)
        assert path[0] == (2, 4)
        assert path[-1] == (6, 4)
        # Path should go around the wall (through y=8)
        assert all(
            level.tiles[x][y].tile_type != TileType.WALL
            for x, y in path[1:]
        )

    def test_path_to_self(self):
        level = Level(9, 9)
        path = level.find_path(4, 4, 4, 4)
        assert path == [(4, 4)]

    def test_diagonal_path(self):
        level = Level(9, 9)
        path = level.find_path(0, 0, 4, 4)
        assert path[0] == (0, 0)
        assert path[-1] == (4, 4)


class TestFOV:
    def test_fov_sees_open_area(self):
        level = Level(9, 9)
        fov = level.compute_fov(4, 4)
        # Should see most of the map from center
        assert fov[4][4]  # See self
        assert fov[0][0]  # Corner visible in open map

    def test_fov_blocked_by_wall(self):
        level = Level(9, 9)
        level.set_tile_type(3, 4, TileType.WALL)
        fov = level.compute_fov(4, 4)
        # Wall itself may be visible, but tiles behind it should not be
        assert not fov[1][4]  # Behind wall

    def test_fov_with_radius(self):
        level = Level(15, 15)
        fov = level.compute_fov(7, 7, radius=3)
        assert fov[7][7]
        assert not fov[0][0]  # Too far


class TestLOS:
    def test_los_open(self):
        level = Level(9, 9)
        assert level.has_los(Point(1, 1), Point(5, 1))

    def test_los_blocked_by_wall(self):
        level = Level(9, 9)
        level.set_tile_type(3, 1, TileType.WALL)
        assert not level.has_los(Point(1, 1), Point(5, 1))

    def test_los_adjacent_always_true(self):
        level = Level(9, 9)
        assert level.has_los(Point(1, 1), Point(2, 1))

    def test_los_to_self(self):
        level = Level(9, 9)
        assert level.has_los(Point(4, 4), Point(4, 4))
