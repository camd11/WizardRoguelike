"""Tests for the Spell base class — stat pipeline, targeting, costs."""
import pytest

from game.constants import Tags, Team
from game.core.level import Level
from game.core.spell_base import Spell
from game.core.types import Point
from game.core.unit import Unit

from tests.conftest import SimpleTestSpell


class TestSpellStatPipeline:
    def test_get_stat_without_caster_returns_base(self):
        s = SimpleTestSpell()
        assert s.get_stat("damage") == 10

    def test_get_stat_with_caster_applies_bonuses(self):
        level = Level(9, 9)
        u = Unit()
        u.team = Team.PLAYER
        level.add_unit(u, 1, 1)
        u.global_bonuses["damage"] = 5
        u.add_spell(s := SimpleTestSpell())
        assert s.get_stat("damage") == 15

    def test_get_stat_tag_bonus(self):
        level = Level(9, 9)
        u = Unit()
        u.team = Team.PLAYER
        level.add_unit(u, 1, 1)
        u.tag_bonuses[Tags.Fire]["damage"] = 3
        u.add_spell(s := SimpleTestSpell())
        assert s.get_stat("damage") == 13


class TestCanCast:
    def test_can_cast_in_range(self):
        level = Level(9, 9)
        player = Unit()
        player.team = Team.PLAYER
        level.add_unit(player, 1, 1)

        enemy = Unit()
        enemy.team = Team.ENEMY
        level.add_unit(enemy, 3, 1)

        s = SimpleTestSpell()
        player.add_spell(s)
        assert s.can_cast(3, 1)

    def test_cannot_cast_out_of_range(self):
        level = Level(9, 9)
        player = Unit()
        player.team = Team.PLAYER
        level.add_unit(player, 0, 0)
        s = SimpleTestSpell()
        player.add_spell(s)
        assert not s.can_cast(8, 8)  # Too far

    def test_cannot_cast_without_los(self):
        from game.constants import TileType
        level = Level(9, 9)
        level.set_tile_type(2, 1, TileType.WALL)
        player = Unit()
        player.team = Team.PLAYER
        level.add_unit(player, 1, 1)
        s = SimpleTestSpell()
        player.add_spell(s)
        assert not s.can_cast(3, 1)

    def test_cannot_cast_out_of_bounds(self):
        level = Level(9, 9)
        player = Unit()
        player.team = Team.PLAYER
        level.add_unit(player, 1, 1)
        s = SimpleTestSpell()
        player.add_spell(s)
        assert not s.can_cast(-1, 0)
        assert not s.can_cast(9, 9)


class TestSpellCosts:
    def test_can_pay_costs_with_charges(self):
        s = SimpleTestSpell()
        u = Unit()
        u.add_spell(s)
        assert s.can_pay_costs()

    def test_cannot_pay_costs_no_charges(self):
        s = SimpleTestSpell()
        s.cur_charges = 0
        u = Unit()
        u.add_spell(s)
        assert not s.can_pay_costs()

    def test_pay_costs_decrements_charges(self):
        s = SimpleTestSpell()
        u = Unit()
        u.add_spell(s)
        s.pay_costs()
        assert s.cur_charges == 2

    def test_cooldown_blocks_casting(self):
        s = SimpleTestSpell()
        s.cool_down = 2
        u = Unit()
        u.add_spell(s)
        s.pay_costs()
        assert s.cur_cool_down == 2
        assert not s.can_pay_costs()

    def test_cooldown_ticks_on_pre_advance(self):
        s = SimpleTestSpell()
        s.cool_down = 2
        u = Unit()
        u.add_spell(s)
        s.pay_costs()
        s.pre_advance()
        assert s.cur_cool_down == 1
        s.pre_advance()
        assert s.cur_cool_down == 0
        assert s.can_pay_costs()


class TestSpellCastGenerator:
    def test_cast_returns_generator(self):
        s = SimpleTestSpell()
        gen = s.cast(3, 3)
        assert hasattr(gen, '__next__')

    def test_cast_deals_damage(self):
        level = Level(9, 9)
        player = Unit()
        player.team = Team.PLAYER
        level.add_unit(player, 1, 1)

        enemy = Unit()
        enemy.team = Team.ENEMY
        enemy.max_hp = 40
        enemy.cur_hp = 40
        level.add_unit(enemy, 3, 1)

        s = SimpleTestSpell()
        player.add_spell(s)

        # Run the generator to completion
        gen = s.cast(3, 1)
        try:
            while True:
                next(gen)
        except StopIteration:
            pass

        assert enemy.cur_hp == 30  # 40 - 10
