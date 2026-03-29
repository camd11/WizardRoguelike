"""Tests for the Buff system — stack types, symmetric apply/unapply, bonuses."""
from game.constants import StackType, Tags
from game.core.buff import Buff
from game.core.unit import Unit


class FireResistBuff(Buff):
    def on_init(self):
        self.name = "Fire Resist"
        self.resists = {Tags.Fire: 50}
        self.stack_type = StackType.STACK_DURATION


class DamageBonusBuff(Buff):
    def on_init(self):
        self.name = "Power Up"
        self.global_bonuses["damage"] = 5
        self.stack_type = StackType.STACK_DURATION


class TagBonusBuff(Buff):
    def on_init(self):
        self.name = "Fire Mastery"
        self.tag_bonuses[Tags.Fire]["damage"] = 3
        self.tag_bonuses_pct[Tags.Fire]["damage"] = 25
        self.stack_type = StackType.STACK_DURATION


class NoStackBuff(Buff):
    def on_init(self):
        self.name = "Unique"
        self.stack_type = StackType.STACK_NONE


class ReplaceBuff(Buff):
    def on_init(self):
        self.name = "Replaceable"
        self.stack_type = StackType.STACK_REPLACE
        self.global_bonuses["damage"] = 10


class IntensityBuff(Buff):
    def on_init(self):
        self.name = "Stacking"
        self.stack_type = StackType.STACK_INTENSITY
        self.global_bonuses["damage"] = 2


class TestResistAccumulation:
    def test_apply_adds_resist(self):
        u = Unit()
        b = FireResistBuff()
        u.apply_buff(b, duration=3)
        assert u.resists[Tags.Fire] == 50

    def test_unapply_removes_resist(self):
        u = Unit()
        b = FireResistBuff()
        u.apply_buff(b, duration=3)
        u.remove_buff(b)
        assert u.resists.get(Tags.Fire, 0) == 0

    def test_multiple_resist_buffs_stack(self):
        u = Unit()
        b1 = FireResistBuff()
        b1.stack_type = StackType.STACK_INTENSITY
        b2 = FireResistBuff()
        b2.stack_type = StackType.STACK_INTENSITY
        u.apply_buff(b1, duration=3)
        u.apply_buff(b2, duration=3)
        assert u.resists[Tags.Fire] == 100


class TestGlobalBonusAccumulation:
    def test_apply_adds_global_bonus(self):
        u = Unit()
        b = DamageBonusBuff()
        u.apply_buff(b, duration=3)
        assert u.global_bonuses["damage"] == 5

    def test_unapply_removes_global_bonus(self):
        u = Unit()
        b = DamageBonusBuff()
        u.apply_buff(b, duration=3)
        u.remove_buff(b)
        assert u.global_bonuses["damage"] == 0

    def test_symmetry_apply_unapply_cycle(self):
        """Applying then removing a buff should leave stats unchanged."""
        u = Unit()
        original_damage = u.global_bonuses["damage"]
        original_fire_resist = u.resists.get(Tags.Fire, 0)

        b = DamageBonusBuff()
        u.apply_buff(b, duration=5)
        u.remove_buff(b)

        assert u.global_bonuses["damage"] == original_damage
        assert u.resists.get(Tags.Fire, 0) == original_fire_resist


class TestTagBonusAccumulation:
    def test_apply_adds_tag_bonus(self):
        u = Unit()
        b = TagBonusBuff()
        u.apply_buff(b, duration=3)
        assert u.tag_bonuses[Tags.Fire]["damage"] == 3
        assert u.tag_bonuses_pct[Tags.Fire]["damage"] == 25

    def test_unapply_removes_tag_bonus(self):
        u = Unit()
        b = TagBonusBuff()
        u.apply_buff(b, duration=3)
        u.remove_buff(b)
        assert u.tag_bonuses[Tags.Fire]["damage"] == 0
        assert u.tag_bonuses_pct[Tags.Fire]["damage"] == 0


class TestStackTypes:
    def test_stack_none_rejects_second(self):
        u = Unit()
        b1 = NoStackBuff()
        b2 = NoStackBuff()
        assert u.apply_buff(b1, duration=5) is True
        assert u.apply_buff(b2, duration=5) is False
        assert len([b for b in u.buffs if b.name == "Unique"]) == 1

    def test_stack_duration_refreshes(self):
        u = Unit()
        b1 = FireResistBuff()
        b2 = FireResistBuff()
        u.apply_buff(b1, duration=2)
        u.apply_buff(b2, duration=5)
        assert b1.turns_left == 5  # Refreshed to max
        assert len([b for b in u.buffs if b.name == "Fire Resist"]) == 1

    def test_stack_replace_removes_old(self):
        u = Unit()
        b1 = ReplaceBuff()
        b2 = ReplaceBuff()
        u.apply_buff(b1, duration=3)
        assert u.global_bonuses["damage"] == 10
        u.apply_buff(b2, duration=3)
        # Old removed, new applied — bonus should still be 10 (not 20)
        assert u.global_bonuses["damage"] == 10
        assert b1 not in u.buffs
        assert b2 in u.buffs

    def test_stack_intensity_allows_multiple(self):
        u = Unit()
        b1 = IntensityBuff()
        b2 = IntensityBuff()
        u.apply_buff(b1, duration=3)
        u.apply_buff(b2, duration=3)
        assert u.global_bonuses["damage"] == 4  # 2 + 2
        assert len([b for b in u.buffs if b.name == "Stacking"]) == 2


class TestBuffLifecycle:
    def test_on_advance_called(self):
        class TickBuff(Buff):
            def on_init(self):
                self.ticks = 0
            def on_advance(self):
                self.ticks += 1

        u = Unit()
        b = TickBuff()
        u.apply_buff(b, duration=5)
        b.advance()
        assert b.ticks == 1

    def test_on_applied_called(self):
        class ApplyTracker(Buff):
            def on_init(self):
                self.applied_to = None
            def on_applied(self, owner):
                self.applied_to = owner

        u = Unit()
        b = ApplyTracker()
        u.apply_buff(b, duration=1)
        assert b.applied_to is u

    def test_on_unapplied_called(self):
        class UnapplyTracker(Buff):
            def on_init(self):
                self.unapplied = False
            def on_unapplied(self):
                self.unapplied = True

        u = Unit()
        b = UnapplyTracker()
        u.apply_buff(b, duration=1)
        u.remove_buff(b)
        assert b.unapplied is True

    def test_auto_removal_at_zero_calls_unapply(self):
        class UnapplyTracker(Buff):
            def on_init(self):
                self.unapplied = False
                self.global_bonuses["damage"] = 5
            def on_unapplied(self):
                self.unapplied = True

        u = Unit()
        b = UnapplyTracker()
        u.apply_buff(b, duration=1)
        assert u.global_bonuses["damage"] == 5
        u.advance_buffs()
        assert b.unapplied is True
        assert u.global_bonuses["damage"] == 0
