"""Props — level objects that exist on tiles: portals, lairs, shrines.

Lairs are the key gameplay mechanic from RW2: destructible spawners
that produce enemies every N turns until destroyed.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from game.constants import Tags, Team

if TYPE_CHECKING:
    from game.core.level import Level
    from game.core.rng import GameRNG
    from game.core.unit import Unit


class Prop:
    """Base class for level props."""

    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y
        self.name = "Prop"

    def advance(self, level: Level) -> None:
        """Called each turn."""
        pass


class ExitPortal(Prop):
    """Level exit — step on it to advance after clearing enemies."""

    def __init__(self, x: int, y: int) -> None:
        super().__init__(x, y)
        self.name = "Exit Portal"


class Lair(Prop):
    """Destructible spawner that produces enemies every N turns.

    RW2's lairs are a core mechanic: they pressure the player to
    push forward and destroy them rather than playing defensively.

    Lairs have HP and can be targeted/damaged. When destroyed,
    they stop spawning.
    """

    def __init__(self, x: int, y: int, spawn_func: Callable[[], Unit],
                 spawn_interval: int = 5, max_hp: int = 15) -> None:
        super().__init__(x, y)
        self.name = "Lair"
        self.spawn_func = spawn_func
        self.spawn_interval = spawn_interval
        self.turns_since_spawn = 0
        self.max_hp = max_hp
        self.cur_hp = max_hp
        self.destroyed = False
        self.team = Team.ENEMY

    def advance(self, level: Level) -> None:
        """Spawn an enemy every spawn_interval turns."""
        if self.destroyed:
            return

        self.turns_since_spawn += 1
        if self.turns_since_spawn >= self.spawn_interval:
            self.turns_since_spawn = 0
            self._spawn(level)

    def take_damage(self, amount: int) -> int:
        """Lairs take damage from spells. Returns actual damage dealt."""
        if self.destroyed:
            return 0
        actual = min(amount, self.cur_hp)
        self.cur_hp -= actual
        if self.cur_hp <= 0:
            self.destroyed = True
        return actual

    def _spawn(self, level: Level) -> None:
        """Spawn an enemy adjacent to the lair."""
        from game.core.types import Point

        origin = Point(self.x, self.y)
        for adj in origin.adjacent():
            if level.in_bounds(adj.x, adj.y):
                tile = level.tiles[adj.x][adj.y]
                if tile.is_floor and tile.unit is None:
                    monster = self.spawn_func()
                    level.add_unit(monster, adj.x, adj.y)
                    return

    def is_alive(self) -> bool:
        return not self.destroyed
