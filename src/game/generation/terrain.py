"""Terrain generation using RW2-style fill → mutate → validate approach.

Rift Wizard 2 generates levels by:
1. Filling the entire grid with walls or chasms
2. Applying 1-5 "seed mutators" that carve patterns (paths, lumps, noise, squares, grids)
3. Applying 0-4 "modifiers" that transform the terrain (symmetry, cellular automata, borders)
4. Validating floor/wall ratios (min 50 floors, min 120 walls)
5. Ensuring all floor tiles form a connected region
6. Populating with monsters, exits, items

This produces organic, varied levels — NOT standard roguelike rooms+corridors.
Each seed mutator creates a radically different base geometry; stacking
mutators creates fractal complexity.

Reference: Dylan White's GDC-style breakdown at gamedeveloper.com/design/generating-cool-levels-for-rift-wizard
"""
from __future__ import annotations

import math
from collections import deque
from typing import TYPE_CHECKING

from game.constants import LEVEL_SIZE, TileType

if TYPE_CHECKING:
    from game.core.level import Level
    from game.core.rng import GameRNG


# ---------------------------------------------------------------------------
# Seed mutators — initial pattern generators
# ---------------------------------------------------------------------------

def seed_paths(level: Level, rng: GameRNG) -> None:
    """Carve winding paths connecting random points.

    Creates corridor networks by connecting 5-20 random points with
    Bresenham lines. Optionally reconnects endpoints for loops.
    """
    num_points = rng.randint(5, 20)
    points = []
    for _ in range(num_points):
        x = rng.randint(1, level.width - 2)
        y = rng.randint(1, level.height - 2)
        points.append((x, y))

    # Connect points sequentially
    for i in range(len(points) - 1):
        _carve_line(level, points[i], points[i + 1])

    # Random reconnections (creates loops)
    reconnect_chance = rng.random() * 0.4
    for i in range(len(points)):
        if rng.random() < reconnect_chance:
            j = rng.randint(0, len(points) - 1)
            if i != j:
                _carve_line(level, points[i], points[j])


def seed_lumps(level: Level, rng: GameRNG) -> None:
    """Grow organic blob regions via flood-fill from random seeds.

    Creates cave-like formations by growing 2-8 blobs of 15-60 tiles each.
    """
    num_lumps = rng.randint(2, 8)
    for _ in range(num_lumps):
        cx = rng.randint(2, level.width - 3)
        cy = rng.randint(2, level.height - 3)
        size = rng.randint(15, 60)
        _grow_blob(level, cx, cy, size, rng)


def seed_noise(level: Level, rng: GameRNG) -> None:
    """Random scattered floor tiles at 15-35% density.

    Creates a noisy, cave-like texture when combined with cellular automata.
    """
    chance = rng.randint(15, 35) / 100.0
    for x in range(1, level.width - 1):
        for y in range(1, level.height - 1):
            if rng.random() < chance:
                level.set_tile_type(x, y, TileType.FLOOR)


def seed_squares(level: Level, rng: GameRNG) -> None:
    """Place random rectangular regions of floor.

    Unlike rooms+corridors, these overlap freely creating irregular shapes.
    """
    num_rects = rng.randint(4, 10)
    for _ in range(num_rects):
        w = rng.randint(3, 8)
        h = rng.randint(3, 8)
        x = rng.randint(1, level.width - w - 1)
        y = rng.randint(1, level.height - h - 1)
        for rx in range(x, min(x + w, level.width - 1)):
            for ry in range(y, min(y + h, level.height - 1)):
                level.set_tile_type(rx, ry, TileType.FLOOR)


def seed_grid(level: Level, rng: GameRNG) -> None:
    """Create a grid pattern of floors with random spacing.

    Produces room-like areas separated by wall pillars.
    """
    spacing = rng.randint(3, 6)
    chance = rng.randint(40, 90) / 100.0
    for x in range(1, level.width - 1):
        for y in range(1, level.height - 1):
            if (x % spacing < spacing - 1) and (y % spacing < spacing - 1):
                if rng.random() < chance:
                    level.set_tile_type(x, y, TileType.FLOOR)


# All seed mutators
SEED_MUTATORS = [seed_paths, seed_lumps, seed_noise, seed_squares, seed_grid]


# ---------------------------------------------------------------------------
# Terrain modifiers — transform existing terrain
# ---------------------------------------------------------------------------

def mod_cellular_automata(level: Level, rng: GameRNG) -> None:
    """Apply Conway-like cellular automata smoothing.

    Tiles with 4+ wall neighbors become walls; tiles with 4+ floor neighbors
    become floors. Creates smooth, organic-looking caves. Run 2-4 iterations.
    """
    iterations = rng.randint(2, 4)
    for _ in range(iterations):
        changes = []
        for x in range(1, level.width - 1):
            for y in range(1, level.height - 1):
                wall_count = _count_wall_neighbors(level, x, y)
                if wall_count >= 5:
                    changes.append((x, y, TileType.WALL))
                elif wall_count <= 3:
                    changes.append((x, y, TileType.FLOOR))
        for x, y, tt in changes:
            level.set_tile_type(x, y, tt)


def mod_symmetry_x(level: Level, rng: GameRNG) -> None:
    """Mirror the left half to the right half (X-axis symmetry)."""
    mid = level.width // 2
    for x in range(mid):
        mirror_x = level.width - 1 - x
        for y in range(level.height):
            level.set_tile_type(mirror_x, y, level.tiles[x][y].tile_type)


def mod_symmetry_y(level: Level, rng: GameRNG) -> None:
    """Mirror the top half to the bottom half (Y-axis symmetry)."""
    mid = level.height // 2
    for x in range(level.width):
        for y in range(mid):
            mirror_y = level.height - 1 - y
            level.set_tile_type(x, mirror_y, level.tiles[x][y].tile_type)


def mod_border(level: Level, rng: GameRNG) -> None:
    """Add a wall border around the level edges."""
    for x in range(level.width):
        level.set_tile_type(x, 0, TileType.WALL)
        level.set_tile_type(x, level.height - 1, TileType.WALL)
    for y in range(level.height):
        level.set_tile_type(0, y, TileType.WALL)
        level.set_tile_type(level.width - 1, y, TileType.WALL)


def mod_expand_floors(level: Level, rng: GameRNG) -> None:
    """Randomly expand floor tiles into adjacent walls (erosion).

    Makes passages wider and caves more open.
    """
    chance = rng.randint(10, 30) / 100.0
    expansions = []
    for x in range(1, level.width - 1):
        for y in range(1, level.height - 1):
            if level.tiles[x][y].is_wall:
                # If adjacent to floor, chance to become floor
                has_floor_neighbor = any(
                    level.tiles[nx][ny].is_floor
                    for nx, ny in [(x-1, y), (x+1, y), (x, y-1), (x, y+1)]
                    if level.in_bounds(nx, ny)
                )
                if has_floor_neighbor and rng.random() < chance:
                    expansions.append((x, y))
    for x, y in expansions:
        level.set_tile_type(x, y, TileType.FLOOR)


def mod_pillars(level: Level, rng: GameRNG) -> None:
    """Add scattered wall pillars in open floor areas.

    Creates tactical cover and interesting movement patterns.
    """
    spacing = rng.randint(3, 5)
    chance = rng.randint(20, 50) / 100.0
    for x in range(2, level.width - 2, spacing):
        for y in range(2, level.height - 2, spacing):
            if level.tiles[x][y].is_floor and rng.random() < chance:
                # Only place pillar if surrounded by mostly floor
                wall_count = _count_wall_neighbors(level, x, y)
                if wall_count <= 2:
                    level.set_tile_type(x, y, TileType.WALL)


# All terrain modifiers
TERRAIN_MODIFIERS = [
    mod_cellular_automata, mod_symmetry_x, mod_symmetry_y,
    mod_border, mod_expand_floors, mod_pillars,
]


# ---------------------------------------------------------------------------
# Main terrain generation pipeline
# ---------------------------------------------------------------------------

MIN_FLOORS = 50
MIN_WALLS = 100

def generate_terrain(level: Level, rng: GameRNG, difficulty: int) -> bool:
    """Generate terrain using RW2-style fill → mutate → validate pipeline.

    Returns True if terrain is valid (floor/wall ratio + connectivity).
    Caller should retry with different seed if False.
    """
    # Step 1: Fill entire level with walls
    for x in range(level.width):
        for y in range(level.height):
            level.set_tile_type(x, y, TileType.WALL)

    # Step 2: Apply 1-3 seed mutators
    num_seeds = rng.randint(1, min(3, 1 + difficulty))
    for _ in range(num_seeds):
        mutator = rng.choice(SEED_MUTATORS)
        mutator(level, rng)

    # Step 3: Apply 0-2 terrain modifiers
    num_mods = rng.randint(0, 2)
    for _ in range(num_mods):
        modifier = rng.choice(TERRAIN_MODIFIERS)
        modifier(level, rng)

    # Step 4: Always apply border (keeps edges clean)
    mod_border(level, rng)

    # Step 5: Validate floor/wall ratio
    floors, walls = _count_tiles(level)
    if floors < MIN_FLOORS or walls < MIN_WALLS:
        # Try to fix: if too few floors, apply expansion; if too few walls, add pillars
        for _ in range(5):
            floors, walls = _count_tiles(level)
            if floors < MIN_FLOORS:
                mod_expand_floors(level, rng)
            elif walls < MIN_WALLS:
                mod_pillars(level, rng)
            else:
                break

    # Step 6: Ensure connectivity
    _ensure_connectivity(level, rng)

    # Final validation
    floors, walls = _count_tiles(level)
    return floors >= MIN_FLOORS and walls >= MIN_WALLS


# ---------------------------------------------------------------------------
# Connectivity assurance
# ---------------------------------------------------------------------------

def _ensure_connectivity(level: Level, rng: GameRNG) -> None:
    """Ensure all floor tiles form a single connected region.

    Uses flood-fill labeling to find disconnected regions, then
    connects them with carved paths (like RW2's ensure_connectivity).
    """
    # Find all connected regions
    regions = _find_floor_regions(level)

    if len(regions) <= 1:
        return  # Already connected

    # Connect each region to the largest one
    largest = max(regions, key=len)
    for region in regions:
        if region is largest:
            continue
        # Find closest pair of points between this region and the largest
        best_dist = float("inf")
        best_a = None
        best_b = None
        # Sample points to avoid O(n²) for large regions
        sample_a = list(region)[:50]
        sample_b = list(largest)[:50]
        for ax, ay in sample_a:
            for bx, by in sample_b:
                dist = abs(ax - bx) + abs(ay - by)
                if dist < best_dist:
                    best_dist = dist
                    best_a = (ax, ay)
                    best_b = (bx, by)

        if best_a and best_b:
            _carve_line(level, best_a, best_b)


def _find_floor_regions(level: Level) -> list[set[tuple[int, int]]]:
    """Find all connected floor regions using flood-fill."""
    visited = set()
    regions = []

    for x in range(level.width):
        for y in range(level.height):
            if not level.tiles[x][y].is_floor or (x, y) in visited:
                continue
            # BFS flood fill
            region = set()
            queue = deque([(x, y)])
            while queue:
                cx, cy = queue.popleft()
                if (cx, cy) in visited:
                    continue
                if not level.in_bounds(cx, cy) or not level.tiles[cx][cy].is_floor:
                    continue
                visited.add((cx, cy))
                region.add((cx, cy))
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = cx + dx, cy + dy
                    if (nx, ny) not in visited:
                        queue.append((nx, ny))
            if region:
                regions.append(region)

    return regions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _carve_line(level: Level, start: tuple[int, int], end: tuple[int, int]) -> None:
    """Carve a floor line between two points using Bresenham's."""
    x0, y0 = start
    x1, y1 = end
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    while True:
        if level.in_bounds(x0, y0):
            level.set_tile_type(x0, y0, TileType.FLOOR)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def _grow_blob(level: Level, cx: int, cy: int, size: int, rng: GameRNG) -> None:
    """Grow an organic blob of floor tiles from a center point."""
    placed = set()
    frontier = [(cx, cy)]
    level.set_tile_type(cx, cy, TileType.FLOOR)
    placed.add((cx, cy))

    while len(placed) < size and frontier:
        idx = rng.randint(0, len(frontier) - 1)
        x, y = frontier.pop(idx)

        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
            nx, ny = x + dx, y + dy
            if (nx, ny) not in placed and level.in_bounds(nx, ny) and 1 <= nx < level.width - 1 and 1 <= ny < level.height - 1:
                if rng.random() < 0.6:
                    level.set_tile_type(nx, ny, TileType.FLOOR)
                    placed.add((nx, ny))
                    frontier.append((nx, ny))
                    if len(placed) >= size:
                        return


def _count_wall_neighbors(level: Level, x: int, y: int) -> int:
    """Count wall tiles in the 8-neighborhood."""
    count = 0
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nx, ny = x + dx, y + dy
            if not level.in_bounds(nx, ny) or level.tiles[nx][ny].is_wall:
                count += 1
    return count


def _count_tiles(level: Level) -> tuple[int, int]:
    """Count floor and wall tiles. Returns (floors, walls)."""
    floors = 0
    walls = 0
    for x in range(level.width):
        for y in range(level.height):
            if level.tiles[x][y].is_floor:
                floors += 1
            elif level.tiles[x][y].is_wall:
                walls += 1
    return floors, walls
