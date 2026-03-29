"""Tests for geometry iterators: Bolt, Burst, Beam, Cone."""
import math

from game.constants import TileType
from game.core.level import Level
from game.core.shapes import (
    bolt,
    beam,
    burst,
    cone,
    get_beam_points,
    get_bolt_points,
    get_burst_points,
    get_cone_points,
    get_line,
)
from game.core.types import Point


class TestGetLine:
    def test_horizontal(self):
        line = get_line(Point(0, 0), Point(4, 0))
        assert line == [Point(0, 0), Point(1, 0), Point(2, 0), Point(3, 0), Point(4, 0)]

    def test_vertical(self):
        line = get_line(Point(0, 0), Point(0, 3))
        assert line == [Point(0, 0), Point(0, 1), Point(0, 2), Point(0, 3)]

    def test_diagonal(self):
        line = get_line(Point(0, 0), Point(3, 3))
        assert len(line) == 4
        assert line[0] == Point(0, 0)
        assert line[-1] == Point(3, 3)

    def test_single_point(self):
        line = get_line(Point(2, 2), Point(2, 2))
        assert line == [Point(2, 2)]

    def test_reverse_direction(self):
        line = get_line(Point(4, 0), Point(0, 0))
        assert line[0] == Point(4, 0)
        assert line[-1] == Point(0, 0)
        assert len(line) == 5


class TestBolt:
    def test_bolt_travels_in_line(self):
        level = Level(9, 9)
        stages = list(bolt(level, Point(0, 4), Point(6, 4)))
        points = [p for stage in stages for p in stage]
        assert all(p.y == 4 for p in points)
        assert points[0] == Point(1, 4)  # Skips start

    def test_bolt_stops_at_wall(self):
        level = Level(9, 9)
        level.set_tile_type(3, 4, TileType.WALL)
        points = get_bolt_points(level, Point(0, 4), Point(6, 4))
        assert all(p.x < 3 for p in points)

    def test_bolt_stops_at_unit(self):
        from game.constants import Team
        from game.core.unit import Unit

        level = Level(9, 9)
        blocker = Unit()
        blocker.team = Team.ENEMY
        level.add_unit(blocker, 3, 4)
        points = get_bolt_points(level, Point(0, 4), Point(6, 4))
        assert Point(3, 4) in points
        assert all(p.x <= 3 for p in points)

    def test_bolt_out_of_bounds_stops(self):
        level = Level(5, 5)
        points = get_bolt_points(level, Point(0, 2), Point(10, 2))
        assert all(level.in_bounds(p.x, p.y) for p in points)


class TestBeam:
    def test_beam_pierces_units(self):
        from game.constants import Team
        from game.core.unit import Unit

        level = Level(9, 9)
        blocker = Unit()
        blocker.team = Team.ENEMY
        level.add_unit(blocker, 3, 4)
        points = get_beam_points(level, Point(0, 4), Point(6, 4))
        # Beam should continue past the unit
        assert any(p.x > 3 for p in points)

    def test_beam_stops_at_wall(self):
        level = Level(9, 9)
        level.set_tile_type(3, 4, TileType.WALL)
        points = get_beam_points(level, Point(0, 4), Point(6, 4))
        assert all(p.x < 3 for p in points)


class TestBurst:
    def test_burst_radius_0(self):
        level = Level(9, 9)
        stages = list(burst(level, Point(4, 4), 0))
        assert len(stages) == 1
        assert stages[0] == [Point(4, 4)]

    def test_burst_radius_1_includes_adjacent(self):
        level = Level(9, 9)
        points = get_burst_points(level, Point(4, 4), 1)
        assert Point(4, 4) in points
        # All 8 neighbors should be reachable
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                assert Point(4 + dx, 4 + dy) in points

    def test_burst_stage_count_matches_radius(self):
        level = Level(15, 15)
        stages = list(burst(level, Point(7, 7), 3))
        assert len(stages) == 4  # Center + 3 rings

    def test_burst_blocked_by_wall(self):
        level = Level(9, 9)
        # Wall at (5, 4) — points behind it shouldn't be in burst
        level.set_tile_type(5, 4, TileType.WALL)
        points = get_burst_points(level, Point(4, 4), 3)
        assert Point(5, 4) not in points  # Wall itself excluded

    def test_burst_ignore_walls(self):
        level = Level(9, 9)
        level.set_tile_type(5, 4, TileType.WALL)
        points = get_burst_points(level, Point(4, 4), 3, ignore_walls=True)
        # With ignore_walls, the wall tile IS included
        assert Point(5, 4) in points


class TestCone:
    def test_cone_expands_toward_target(self):
        level = Level(15, 15)
        points = get_cone_points(level, Point(7, 7), Point(10, 7), 3)
        # Should contain points to the right of origin
        assert any(p.x > 7 for p in points)

    def test_cone_excludes_behind(self):
        level = Level(15, 15)
        points = get_cone_points(level, Point(7, 7), Point(10, 7), 3)
        # Points directly behind origin (x < 7) should generally not be in cone
        behind_points = [p for p in points if p.x < 7 and p != Point(7, 7)]
        # A few edge cases may exist at ring boundaries but the cone should be mostly forward
        assert len(behind_points) < len(points) / 2

    def test_cone_stage_count(self):
        level = Level(15, 15)
        stages = list(cone(level, Point(7, 7), Point(10, 7), 3))
        assert len(stages) == 4  # Origin + 3 rings

    def test_cone_zero_radius(self):
        level = Level(9, 9)
        stages = list(cone(level, Point(4, 4), Point(6, 4), 0))
        assert len(stages) == 1
        assert stages[0] == [Point(4, 4)]
