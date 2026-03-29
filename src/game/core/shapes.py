"""Geometry iterators for spell targeting: Bolt, Burst, Beam, Cone.

Each function yields stages (lists of Points). Spells iterate stages
and yield between them for animation pacing.

Replicates RW2 Level.py:187-263 patterns.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING, Generator

from game.core.types import Point

if TYPE_CHECKING:
    from game.core.level import Level


def get_line(start: Point, end: Point) -> list[Point]:
    """Bresenham's line algorithm. Returns all points from start to end inclusive."""
    points = []
    x0, y0 = start.x, start.y
    x1, y1 = end.x, end.y

    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    while True:
        points.append(Point(x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy

    return points


def bolt(level: Level, start: Point, end: Point) -> Generator[list[Point], None, None]:
    """Projectile along a line. Yields one point per stage.

    Stops at walls. Does NOT include the start point.
    """
    line = get_line(start, end)
    for p in line[1:]:  # Skip start
        if not level.in_bounds(p.x, p.y):
            return
        if level.tiles[p.x][p.y].is_wall:
            return
        yield [p]
        # Stop at first unit hit (for non-beam bolts)
        if level.get_unit_at(p.x, p.y) is not None:
            return


def beam(level: Level, start: Point, end: Point) -> Generator[list[Point], None, None]:
    """Piercing line — like bolt but doesn't stop at units, only walls."""
    line = get_line(start, end)
    for p in line[1:]:
        if not level.in_bounds(p.x, p.y):
            return
        if level.tiles[p.x][p.y].is_wall:
            return
        yield [p]


def burst(level: Level, origin: Point, radius: int,
          ignore_walls: bool = False) -> Generator[list[Point], None, None]:
    """Expanding rings from origin. Yields one ring per stage.

    Ring N contains all points at Euclidean distance (N-0.5, N+0.5] from origin
    that have LOS to origin (unless ignore_walls).
    """
    if radius == 0:
        yield [origin]
        return

    yield [origin]

    for ring in range(1, radius + 1):
        points = []
        for dx in range(-ring, ring + 1):
            for dy in range(-ring, ring + 1):
                dist = math.sqrt(dx * dx + dy * dy)
                if dist > ring + 0.5 or dist <= ring - 0.5:
                    continue
                p = Point(origin.x + dx, origin.y + dy)
                if not level.in_bounds(p.x, p.y):
                    continue
                if level.tiles[p.x][p.y].is_wall and not ignore_walls:
                    continue
                if not ignore_walls and not level.has_los(origin, p):
                    continue
                points.append(p)
        if points:
            yield points


def cone(level: Level, origin: Point, target: Point,
         radius: int) -> Generator[list[Point], None, None]:
    """Cone/breath from origin toward target. ~90 degree arc, expanding.

    Yields one ring per stage.
    """
    if radius == 0:
        yield [origin]
        return

    # Direction angle from origin to target
    dx = target.x - origin.x
    dy = target.y - origin.y
    if dx == 0 and dy == 0:
        yield [origin]
        return

    base_angle = math.atan2(dy, dx)
    half_arc = math.pi / 4  # 45 degrees each side = 90 degree cone

    yield [origin]

    for ring in range(1, radius + 1):
        points = []
        for ddx in range(-ring, ring + 1):
            for ddy in range(-ring, ring + 1):
                dist = math.sqrt(ddx * ddx + ddy * ddy)
                if dist > ring + 0.5 or dist <= ring - 0.5:
                    continue
                p = Point(origin.x + ddx, origin.y + ddy)
                if not level.in_bounds(p.x, p.y):
                    continue
                if level.tiles[p.x][p.y].is_wall:
                    continue
                # Angle check
                angle = math.atan2(ddy, ddx)
                diff = abs(angle - base_angle)
                if diff > math.pi:
                    diff = 2 * math.pi - diff
                if diff > half_arc:
                    continue
                points.append(p)
        if points:
            yield points


def get_burst_points(level: Level, origin: Point, radius: int,
                     ignore_walls: bool = False) -> list[Point]:
    """Flat list of all points in a burst (for get_impacted_tiles)."""
    result = []
    for stage in burst(level, origin, radius, ignore_walls):
        result.extend(stage)
    return result


def get_cone_points(level: Level, origin: Point, target: Point,
                    radius: int) -> list[Point]:
    """Flat list of all points in a cone."""
    result = []
    for stage in cone(level, origin, target, radius):
        result.extend(stage)
    return result


def get_bolt_points(level: Level, start: Point, end: Point) -> list[Point]:
    """Flat list of bolt path points (stops at wall/unit)."""
    result = []
    for stage in bolt(level, start, end):
        result.extend(stage)
    return result


def get_beam_points(level: Level, start: Point, end: Point) -> list[Point]:
    """Flat list of beam path points (stops at wall only)."""
    result = []
    for stage in beam(level, start, end):
        result.extend(stage)
    return result
