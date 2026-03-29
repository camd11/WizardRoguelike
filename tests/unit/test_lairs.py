"""Tests for the lair spawner system."""
from game.constants import Tags, Team
from game.core.level import Level
from game.core.prop import Lair
from game.core.unit import Unit
from game.content.monsters.tier1 import make_rat


class TestLairBasics:
    def test_lair_creation(self):
        lair = Lair(5, 5, make_rat, spawn_interval=3, max_hp=10)
        assert lair.cur_hp == 10
        assert not lair.destroyed
        assert lair.is_alive()

    def test_lair_takes_damage(self):
        lair = Lair(5, 5, make_rat, max_hp=10)
        dealt = lair.take_damage(5)
        assert dealt == 5
        assert lair.cur_hp == 5
        assert not lair.destroyed

    def test_lair_destroyed_at_zero_hp(self):
        lair = Lair(5, 5, make_rat, max_hp=10)
        lair.take_damage(10)
        assert lair.destroyed
        assert not lair.is_alive()

    def test_lair_overkill_capped(self):
        lair = Lair(5, 5, make_rat, max_hp=10)
        dealt = lair.take_damage(100)
        assert dealt == 10

    def test_no_damage_when_destroyed(self):
        lair = Lair(5, 5, make_rat, max_hp=10)
        lair.take_damage(10)
        dealt = lair.take_damage(5)
        assert dealt == 0


class TestLairSpawning:
    def test_lair_spawns_after_interval(self):
        level = Level(9, 9)
        lair = Lair(4, 4, make_rat, spawn_interval=2, max_hp=10)
        tile = level.get_tile(4, 4)
        tile.prop = lair

        # Turn 1: no spawn
        lair.advance(level)
        enemies = [u for u in level.units if u.team == Team.ENEMY]
        assert len(enemies) == 0

        # Turn 2: spawn!
        lair.advance(level)
        enemies = [u for u in level.units if u.team == Team.ENEMY]
        assert len(enemies) == 1
        assert enemies[0].name == "Giant Rat"

    def test_destroyed_lair_stops_spawning(self):
        level = Level(9, 9)
        lair = Lair(4, 4, make_rat, spawn_interval=1, max_hp=10)
        tile = level.get_tile(4, 4)
        tile.prop = lair

        lair.take_damage(10)
        assert lair.destroyed

        lair.advance(level)
        enemies = [u for u in level.units if u.team == Team.ENEMY]
        assert len(enemies) == 0


class TestLairInLevel:
    def test_level_not_clear_with_active_lair(self):
        level = Level(9, 9)
        lair = Lair(4, 4, make_rat, spawn_interval=5, max_hp=10)
        tile = level.get_tile(4, 4)
        tile.prop = lair
        assert not level.is_clear()  # Lair exists

    def test_level_clear_after_lair_destroyed(self):
        level = Level(9, 9)
        lair = Lair(4, 4, make_rat, spawn_interval=5, max_hp=10)
        tile = level.get_tile(4, 4)
        tile.prop = lair

        lair.take_damage(10)
        assert level.is_clear()  # No enemies, lair destroyed

    def test_spell_damage_hits_lair(self):
        level = Level(9, 9)
        lair = Lair(4, 4, make_rat, spawn_interval=5, max_hp=10)
        tile = level.get_tile(4, 4)
        tile.prop = lair

        # Deal damage to lair tile (no unit present)
        dealt = level.deal_damage(4, 4, 5, Tags.Fire, source=None)
        assert dealt == 5
        assert lair.cur_hp == 5
