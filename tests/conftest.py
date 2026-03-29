"""Shared test fixtures for all test modules."""
from __future__ import annotations

import pytest

from game.constants import Tags, Team, TileType
from game.core.level import Level
from game.core.rng import GameRNG
from game.core.spell_base import Spell
from game.core.types import Point
from game.core.unit import Unit


@pytest.fixture
def rng() -> GameRNG:
    """Deterministic RNG for reproducible tests."""
    return GameRNG(seed=42)


@pytest.fixture
def small_level() -> Level:
    """A small 9x9 level for unit tests. All floor tiles."""
    return Level(width=9, height=9)


@pytest.fixture
def walled_level() -> Level:
    """9x9 level with walls forming a corridor for LOS/pathfinding tests.

    Layout (. = floor, # = wall):
        .........
        .###.....
        .#.#.....
        .###.....
        .........
        .........
        .........
        .........
        .........
    """
    level = Level(width=9, height=9)
    walls = [(1, 1), (2, 1), (3, 1),
             (1, 2), (3, 2),
             (1, 3), (2, 3), (3, 3)]
    for x, y in walls:
        level.set_tile_type(x, y, TileType.WALL)
    return level


@pytest.fixture
def player() -> Unit:
    """A player unit with 100 HP."""
    unit = Unit()
    unit.name = "Player"
    unit.team = Team.PLAYER
    unit.max_hp = 100
    unit.cur_hp = 100
    return unit


@pytest.fixture
def enemy() -> Unit:
    """An enemy unit with 40 HP."""
    unit = Unit()
    unit.name = "Enemy"
    unit.team = Team.ENEMY
    unit.max_hp = 40
    unit.cur_hp = 40
    return unit


@pytest.fixture
def level_with_player(small_level: Level, player: Unit) -> Level:
    """9x9 level with a player at (1, 1)."""
    small_level.add_unit(player, 1, 1)
    return small_level


@pytest.fixture
def level_with_combatants(small_level: Level, player: Unit, enemy: Unit) -> Level:
    """9x9 level with player at (1,1) and enemy at (5,1)."""
    small_level.add_unit(player, 1, 1)
    small_level.add_unit(enemy, 5, 1)
    return small_level


class SimpleTestSpell(Spell):
    """A trivial spell for testing: deals 10 Fire damage at range 5."""

    def on_init(self) -> None:
        self.name = "Test Bolt"
        self.damage = 10
        self.damage_type = Tags.Fire
        self.range = 5
        self.max_charges = 3
        self.cur_charges = 3
        self.tags = [Tags.Fire, Tags.Sorcery]

    def cast(self, x, y):
        if self.level is not None:
            self.level.deal_damage(x, y, self.get_stat("damage"), self.damage_type, self)
        yield

    def get_impacted_tiles(self, x, y):
        return [Point(x, y)]


@pytest.fixture
def test_spell() -> SimpleTestSpell:
    """A simple Fire bolt spell for testing."""
    return SimpleTestSpell()
