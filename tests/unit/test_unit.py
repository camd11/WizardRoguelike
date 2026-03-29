"""Tests for the Unit class — stat pipeline, buff management, basic behavior."""
from collections import defaultdict

from game.constants import Tags, Team
from game.core.buff import Buff
from game.core.unit import Unit


class TestUnitBasics:
    def test_initial_state(self):
        u = Unit()
        assert u.is_alive()
        assert u.cur_hp == u.max_hp
        assert u.team == Team.ENEMY
        assert u.shields == 0
        assert u.killed is False

    def test_kill(self):
        u = Unit()
        u.kill()
        assert not u.is_alive()
        assert u.killed
        assert u.cur_hp == 0

    def test_is_player(self):
        u = Unit()
        assert not u.is_player()
        u.team = Team.PLAYER
        assert u.is_player()


class TestStatPipeline:
    def test_no_bonuses_returns_base(self):
        from game.core.spell_base import Spell
        u = Unit()
        s = Spell()
        s.tags = [Tags.Fire]
        assert u.get_stat(10, s, "damage") == 10

    def test_global_absolute_bonus(self):
        from game.core.spell_base import Spell
        u = Unit()
        u.global_bonuses["damage"] = 5
        s = Spell()
        s.tags = [Tags.Fire]
        assert u.get_stat(10, s, "damage") == 15

    def test_global_pct_bonus(self):
        from game.core.spell_base import Spell
        u = Unit()
        u.global_bonuses_pct["damage"] = 50  # +50%
        s = Spell()
        s.tags = [Tags.Fire]
        # floor(10 * 150/100) = 15
        assert u.get_stat(10, s, "damage") == 15

    def test_tag_absolute_bonus_matching(self):
        from game.core.spell_base import Spell
        u = Unit()
        u.tag_bonuses[Tags.Fire]["damage"] = 3
        s = Spell()
        s.tags = [Tags.Fire]
        assert u.get_stat(10, s, "damage") == 13

    def test_tag_bonus_non_matching_tag_ignored(self):
        from game.core.spell_base import Spell
        u = Unit()
        u.tag_bonuses[Tags.Ice]["damage"] = 3
        s = Spell()
        s.tags = [Tags.Fire]
        assert u.get_stat(10, s, "damage") == 10

    def test_tag_pct_bonus(self):
        from game.core.spell_base import Spell
        u = Unit()
        u.tag_bonuses_pct[Tags.Fire]["damage"] = 100  # +100%
        s = Spell()
        s.tags = [Tags.Fire]
        # floor(10 * 200/100) = 20
        assert u.get_stat(10, s, "damage") == 20

    def test_multiple_tag_bonuses_stack(self):
        from game.core.spell_base import Spell
        u = Unit()
        u.tag_bonuses[Tags.Fire]["damage"] = 2
        u.tag_bonuses[Tags.Sorcery]["damage"] = 3
        s = Spell()
        s.tags = [Tags.Fire, Tags.Sorcery]
        # 10 + 2 + 3 = 15
        assert u.get_stat(10, s, "damage") == 15

    def test_combined_global_and_tag_bonuses(self):
        from game.core.spell_base import Spell
        u = Unit()
        u.global_bonuses["damage"] = 2
        u.global_bonuses_pct["damage"] = 50
        u.tag_bonuses[Tags.Fire]["damage"] = 3
        u.tag_bonuses_pct[Tags.Fire]["damage"] = 50
        s = Spell()
        s.tags = [Tags.Fire]
        # pct = 50 + 50 = 100, abs = 2 + 3 = 5
        # floor(10 * 200/100) + 5 = 25
        assert u.get_stat(10, s, "damage") == 25

    def test_result_never_negative(self):
        from game.core.spell_base import Spell
        u = Unit()
        u.global_bonuses["damage"] = -100
        s = Spell()
        s.tags = []
        assert u.get_stat(10, s, "damage") == 0


class TestBuffManagement:
    def test_apply_buff(self):
        u = Unit()
        b = Buff()
        b.name = "Test"
        result = u.apply_buff(b, duration=3)
        assert result is True
        assert b in u.buffs
        assert b.turns_left == 3
        assert b.owner is u

    def test_remove_buff(self):
        u = Unit()
        b = Buff()
        u.apply_buff(b, duration=5)
        u.remove_buff(b)
        assert b not in u.buffs
        assert b.owner is None

    def test_get_buff(self):
        u = Unit()
        b = Buff()
        u.apply_buff(b)
        assert u.get_buff(Buff) is b
        assert u.has_buff(Buff) is True

    def test_get_buff_returns_none_when_absent(self):
        u = Unit()
        assert u.get_buff(Buff) is None
        assert u.has_buff(Buff) is False

    def test_advance_buffs_ticks_duration(self):
        u = Unit()
        b = Buff()
        u.apply_buff(b, duration=2)
        u.advance_buffs()
        assert b.turns_left == 1
        assert b in u.buffs

    def test_advance_buffs_removes_at_zero(self):
        u = Unit()
        b = Buff()
        u.apply_buff(b, duration=1)
        u.advance_buffs()
        assert b.turns_left == 0
        assert b not in u.buffs

    def test_permanent_buff_never_expires(self):
        u = Unit()
        b = Buff()
        u.apply_buff(b, duration=0)  # permanent
        for _ in range(100):
            u.advance_buffs()
        assert b in u.buffs


class TestSpellManagement:
    def test_add_spell(self):
        from game.core.spell_base import Spell
        u = Unit()
        s = Spell()
        u.add_spell(s)
        assert s in u.spells
        assert s.caster is u

    def test_remove_spell(self):
        from game.core.spell_base import Spell
        u = Unit()
        s = Spell()
        u.add_spell(s)
        u.remove_spell(s)
        assert s not in u.spells
        assert s.caster is None
