"""Tests for the damage pipeline in Level.deal_damage()."""
import pytest

from game.constants import DAMAGE_INSTANCE_CAP, Tags, Team
from game.core.events import EventOnDamaged, EventOnDeath, EventOnHealed, EventOnPreDamaged
from game.core.level import Level
from game.core.unit import Unit


@pytest.fixture
def combat_level():
    """Level with player at (1,1) and enemy at (5,1)."""
    level = Level(9, 9)
    player = Unit()
    player.name = "Player"
    player.team = Team.PLAYER
    player.max_hp = 100
    player.cur_hp = 100
    level.add_unit(player, 1, 1)

    enemy = Unit()
    enemy.name = "Enemy"
    enemy.team = Team.ENEMY
    enemy.max_hp = 40
    enemy.cur_hp = 40
    level.add_unit(enemy, 5, 1)

    return level, player, enemy


class TestBasicDamage:
    def test_deal_damage_reduces_hp(self, combat_level):
        level, _, enemy = combat_level
        dealt = level.deal_damage(5, 1, 10, Tags.Fire, source=None)
        assert dealt == 10
        assert enemy.cur_hp == 30

    def test_deal_damage_to_empty_tile_returns_zero(self, combat_level):
        level, _, _ = combat_level
        dealt = level.deal_damage(3, 3, 10, Tags.Fire, source=None)
        assert dealt == 0

    def test_damage_capped_at_current_hp(self, combat_level):
        level, _, enemy = combat_level
        dealt = level.deal_damage(5, 1, 999, Tags.Fire, source=None)
        assert dealt == 40
        assert enemy.cur_hp == 0

    def test_zero_damage_returns_zero(self, combat_level):
        level, _, enemy = combat_level
        dealt = level.deal_damage(5, 1, 0, Tags.Fire, source=None)
        assert dealt == 0
        assert enemy.cur_hp == 40


class TestResistance:
    def test_50_pct_resist_halves_damage(self, combat_level):
        level, _, enemy = combat_level
        enemy.resists[Tags.Fire] = 50
        dealt = level.deal_damage(5, 1, 10, Tags.Fire, source=None)
        assert dealt == 5
        assert enemy.cur_hp == 35

    def test_100_pct_resist_blocks_all(self, combat_level):
        level, _, enemy = combat_level
        enemy.resists[Tags.Fire] = 100
        dealt = level.deal_damage(5, 1, 10, Tags.Fire, source=None)
        assert dealt == 0
        assert enemy.cur_hp == 40

    def test_negative_resist_amplifies_damage(self, combat_level):
        level, _, enemy = combat_level
        enemy.resists[Tags.Fire] = -50
        # 10 * (100 - (-50)) / 100 = 10 * 1.5 = 15
        dealt = level.deal_damage(5, 1, 10, Tags.Fire, source=None)
        assert dealt == 15
        assert enemy.cur_hp == 25

    def test_resist_capped_at_100(self, combat_level):
        level, _, enemy = combat_level
        enemy.resists[Tags.Fire] = 200  # Exceeds cap
        dealt = level.deal_damage(5, 1, 10, Tags.Fire, source=None)
        assert dealt == 0  # Capped at 100% resist

    def test_resist_applies_per_damage_type(self, combat_level):
        level, _, enemy = combat_level
        enemy.resists[Tags.Fire] = 100
        # Lightning should not be resisted
        dealt = level.deal_damage(5, 1, 10, Tags.Lightning, source=None)
        assert dealt == 10


class TestShields:
    def test_shield_blocks_damage(self, combat_level):
        level, _, enemy = combat_level
        enemy.shields = 2
        dealt = level.deal_damage(5, 1, 10, Tags.Fire, source=None)
        assert dealt == 0
        assert enemy.shields == 1
        assert enemy.cur_hp == 40

    def test_shield_consumed_per_hit(self, combat_level):
        level, _, enemy = combat_level
        enemy.shields = 1
        level.deal_damage(5, 1, 10, Tags.Fire, source=None)
        assert enemy.shields == 0
        # Second hit should deal damage
        dealt = level.deal_damage(5, 1, 10, Tags.Fire, source=None)
        assert dealt == 10


class TestDeath:
    def test_lethal_damage_kills(self, combat_level):
        level, _, enemy = combat_level
        level.deal_damage(5, 1, 40, Tags.Fire, source=None)
        assert not enemy.is_alive()
        assert enemy.killed

    def test_overkill_caps_damage(self, combat_level):
        level, _, enemy = combat_level
        dealt = level.deal_damage(5, 1, 100, Tags.Fire, source=None)
        assert dealt == 40  # Capped at cur_hp

    def test_dead_unit_removed_from_tile(self, combat_level):
        level, _, enemy = combat_level
        level.deal_damage(5, 1, 40, Tags.Fire, source=None)
        assert level.get_unit_at(5, 1) is None


class TestDamageInstanceCap:
    def test_cap_prevents_infinite_loops(self):
        level = Level(9, 9)
        tank = Unit()
        tank.name = "Tank"
        tank.team = Team.ENEMY
        tank.max_hp = 1000
        tank.cur_hp = 1000
        level.add_unit(tank, 5, 1)

        for _ in range(DAMAGE_INSTANCE_CAP):
            level.deal_damage(5, 1, 1, Tags.Fire, source=None)
        assert tank.cur_hp == 1000 - DAMAGE_INSTANCE_CAP
        # Next hit should be blocked by cap
        dealt = level.deal_damage(5, 1, 1, Tags.Fire, source=None)
        assert dealt == 0


class TestDamageEvents:
    def test_event_on_damaged_fires(self, combat_level):
        level, _, enemy = combat_level
        received = []
        level.event_handler.subscribe(EventOnDamaged, lambda e: received.append(e), entity=enemy)
        level.deal_damage(5, 1, 10, Tags.Fire, source=None)
        assert len(received) == 1
        assert received[0].damage == 10
        assert received[0].damage_type is Tags.Fire

    def test_event_on_pre_damaged_fires(self, combat_level):
        level, _, enemy = combat_level
        received = []
        level.event_handler.subscribe(EventOnPreDamaged, lambda e: received.append(e), entity=enemy)
        level.deal_damage(5, 1, 10, Tags.Fire, source=None)
        assert len(received) == 1

    def test_event_on_death_fires(self, combat_level):
        level, _, enemy = combat_level
        received = []
        level.event_handler.subscribe(EventOnDeath, lambda e: received.append(e), entity=enemy)
        level.deal_damage(5, 1, 40, Tags.Fire, source=None)
        assert len(received) == 1
        assert received[0].unit is enemy

    def test_no_death_event_for_non_lethal(self, combat_level):
        level, _, enemy = combat_level
        received = []
        level.event_handler.subscribe(EventOnDeath, lambda e: received.append(e), entity=enemy)
        level.deal_damage(5, 1, 10, Tags.Fire, source=None)
        assert len(received) == 0

    def test_no_damaged_event_when_shielded(self, combat_level):
        level, _, enemy = combat_level
        enemy.shields = 1
        received = []
        level.event_handler.subscribe(EventOnDamaged, lambda e: received.append(e), entity=enemy)
        level.deal_damage(5, 1, 10, Tags.Fire, source=None)
        assert len(received) == 0
