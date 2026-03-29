"""Integration tests for stun/freeze mechanics during the turn loop."""
import pytest

from game.constants import Tags, Team
from game.content.buffs_common import FreezeBuff, StunBuff
from game.core.actions import PassAction
from game.core.level import Level
from game.core.spell_base import Spell
from game.core.types import Point
from game.core.unit import Unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TrackingSpell(Spell):
    """A melee spell that tracks whether it was used."""
    acted = False

    def on_init(self) -> None:
        self.name = "Track Attack"
        self.damage = 5
        self.damage_type = Tags.Physical
        self.range = 1
        self.melee = True
        self.max_charges = 99
        self.cur_charges = 99
        self.tags = [Tags.Physical]

    def cast(self, x, y):
        TrackingSpell.acted = True
        if self.level:
            self.level.deal_damage(x, y, self.get_stat("damage"), self.damage_type, self)
        yield


def _setup_combat() -> tuple[Level, Unit, Unit]:
    """Create a level with a player at (1,4) and an enemy at (2,4)."""
    level = Level(9, 9)
    player = Unit()
    player.name = "Player"
    player.team = Team.PLAYER
    player.max_hp = 100
    player.cur_hp = 100
    level.add_unit(player, 1, 4)

    enemy = Unit()
    enemy.name = "Goblin"
    enemy.team = Team.ENEMY
    enemy.max_hp = 40
    enemy.cur_hp = 40
    level.add_unit(enemy, 2, 4)
    # Give enemy a melee attack so it normally would act
    enemy.add_spell(TrackingSpell())

    return level, player, enemy


def _advance_one_turn(level: Level) -> None:
    """Advance the level by one full turn.

    Sends a PassAction during the player phase and lets the AI phase run.
    """
    gen = level.iter_frame()
    while True:
        try:
            awaiting = next(gen)
        except StopIteration:
            break
        if level.is_awaiting_input:
            try:
                awaiting = gen.send(PassAction())
            except StopIteration:
                break
        # When we get True, the turn is complete
        if awaiting is True:
            break


# ---------------------------------------------------------------------------
# Stun tests
# ---------------------------------------------------------------------------

class TestStunPreventsAction:
    def test_stunned_enemy_does_not_act(self):
        level, player, enemy = _setup_combat()
        hp_before = player.cur_hp

        stun = StunBuff()
        enemy.apply_buff(stun, duration=3)
        assert any(b.name == "Stunned" for b in enemy.buffs)

        TrackingSpell.acted = False
        _advance_one_turn(level)

        assert not TrackingSpell.acted, "Stunned enemy should not have used its spell"
        assert player.cur_hp == hp_before, "Player should not have taken damage"

    def test_stun_wears_off_after_duration(self):
        level, player, enemy = _setup_combat()

        stun = StunBuff()
        enemy.apply_buff(stun, duration=2)

        # Turn 1: stunned
        _advance_one_turn(level)
        # Turn 2: still stunned (duration ticks from 2 to 1 after turn 1, to 0 after turn 2)
        _advance_one_turn(level)

        # Stun should be removed now (duration was 2, ticked twice)
        has_stun = any(b.name == "Stunned" for b in enemy.buffs)
        assert not has_stun, "Stun should have worn off after 2 turns"


# ---------------------------------------------------------------------------
# Freeze tests
# ---------------------------------------------------------------------------

class TestFreezePreventsAction:
    def test_frozen_enemy_does_not_act(self):
        level, player, enemy = _setup_combat()
        hp_before = player.cur_hp

        freeze = FreezeBuff()
        enemy.apply_buff(freeze, duration=3)
        assert any(b.name == "Frozen" for b in enemy.buffs)

        TrackingSpell.acted = False
        _advance_one_turn(level)

        assert not TrackingSpell.acted, "Frozen enemy should not have used its spell"
        assert player.cur_hp == hp_before, "Player should not have taken damage"

    def test_freeze_has_correct_name(self):
        buff = FreezeBuff()
        assert buff.name == "Frozen"

    def test_stun_has_correct_name(self):
        buff = StunBuff()
        assert buff.name == "Stunned"


# ---------------------------------------------------------------------------
# Both stun/freeze detected by same check in level.py
# ---------------------------------------------------------------------------

class TestStunFreezeInLevelLoop:
    def test_stunned_check_matches_buff_names(self):
        """The level loop checks b.name in ('Stunned', 'Frozen') to skip turns.

        Verify both buff classes produce exactly these names.
        """
        stun = StunBuff()
        freeze = FreezeBuff()
        assert stun.name == "Stunned"
        assert freeze.name == "Frozen"
