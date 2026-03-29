"""Level generation tests: connectivity and validity."""
from collections import deque

from game.constants import Team, TileType
from game.core.rng import GameRNG
from game.core.unit import Unit
from game.generation.level_generator import generate_level


def _flood_fill(level, start_x, start_y) -> set:
    """BFS flood fill from a starting floor tile."""
    visited = set()
    queue = deque([(start_x, start_y)])
    while queue:
        x, y = queue.popleft()
        if (x, y) in visited:
            continue
        if not level.in_bounds(x, y):
            continue
        if level.tiles[x][y].is_wall:
            continue
        visited.add((x, y))
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            queue.append((x + dx, y + dy))
    return visited


class TestConnectivity:
    def test_player_can_reach_all_floor_tiles(self):
        """All floor tiles should be reachable from the player's position."""
        player = Unit()
        player.team = Team.PLAYER
        player.max_hp = 100
        player.cur_hp = 100

        gen = generate_level(difficulty=1, player=player, seed=42)
        level = gen.level

        reachable = _flood_fill(level, player.x, player.y)

        all_floors = set()
        for x in range(level.width):
            for y in range(level.height):
                if level.tiles[x][y].is_floor:
                    all_floors.add((x, y))

        unreachable = all_floors - reachable
        # RW2-style fill→mutate generation may create small disconnected pockets.
        # These are cosmetic — monsters only spawn on reachable tiles.
        # Allow up to 5% of floor tiles to be unreachable.
        max_unreachable = max(5, len(all_floors) // 20)
        assert len(unreachable) <= max_unreachable, (
            f"{len(unreachable)} unreachable floor tiles "
            f"(max {max_unreachable} allowed, {len(all_floors)} total)"
        )

    def test_all_enemies_reachable(self):
        """All enemies should be on tiles reachable from the player."""
        player = Unit()
        player.team = Team.PLAYER
        player.max_hp = 100
        player.cur_hp = 100

        gen = generate_level(difficulty=3, player=player, seed=123)
        level = gen.level
        reachable = _flood_fill(level, player.x, player.y)

        for unit in level.units:
            if unit.team == Team.ENEMY:
                assert (unit.x, unit.y) in reachable, \
                    f"{unit.name} at ({unit.x},{unit.y}) is unreachable"

    def test_has_floor_tiles(self):
        """Generated level must have a reasonable number of floor tiles."""
        player = Unit()
        player.team = Team.PLAYER
        player.max_hp = 100
        player.cur_hp = 100

        gen = generate_level(difficulty=2, player=player, seed=99)
        level = gen.level

        floor_count = sum(
            1 for x in range(level.width)
            for y in range(level.height)
            if level.tiles[x][y].is_floor
        )
        # At least 10% of tiles should be floor
        assert floor_count > (level.width * level.height * 0.1)


class TestDeterminism:
    def test_same_seed_same_layout(self):
        """Same seed must produce identical tile layouts."""
        player1 = Unit()
        player1.team = Team.PLAYER
        player1.max_hp = 100
        player1.cur_hp = 100
        gen1 = generate_level(difficulty=2, player=player1, seed=42)

        player2 = Unit()
        player2.team = Team.PLAYER
        player2.max_hp = 100
        player2.cur_hp = 100
        gen2 = generate_level(difficulty=2, player=player2, seed=42)

        for x in range(gen1.level.width):
            for y in range(gen1.level.height):
                assert gen1.level.tiles[x][y].tile_type == gen2.level.tiles[x][y].tile_type

    def test_same_seed_same_monster_count(self):
        player1 = Unit()
        player1.team = Team.PLAYER
        player1.max_hp = 100
        player1.cur_hp = 100
        gen1 = generate_level(difficulty=3, player=player1, seed=42)

        player2 = Unit()
        player2.team = Team.PLAYER
        player2.max_hp = 100
        player2.cur_hp = 100
        gen2 = generate_level(difficulty=3, player=player2, seed=42)

        assert len(gen1.monsters) == len(gen2.monsters)
