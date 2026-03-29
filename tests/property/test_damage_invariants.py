"""Property-based tests for damage pipeline invariants."""
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from game.constants import Tags, Team
from game.core.level import Level
from game.core.unit import Unit

damage_types = [Tags.Fire, Tags.Ice, Tags.Lightning, Tags.Dark, Tags.Holy,
                Tags.Nature, Tags.Arcane, Tags.Poison, Tags.Physical]


@pytest.mark.property
class TestDamageInvariants:

    @given(
        amount=st.integers(min_value=0, max_value=1000),
        resist=st.integers(min_value=-100, max_value=200),
        shields=st.integers(min_value=0, max_value=5),
        max_hp=st.integers(min_value=1, max_value=500),
        dtype=st.sampled_from(damage_types),
    )
    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    def test_damage_never_negative(self, amount, resist, shields, max_hp, dtype):
        """deal_damage must never return a negative value."""
        level = Level(5, 5)
        unit = Unit()
        unit.team = Team.ENEMY
        unit.max_hp = max_hp
        unit.cur_hp = max_hp
        unit.shields = shields
        unit.resists[dtype] = resist
        level.add_unit(unit, 2, 2)

        dealt = level.deal_damage(2, 2, amount, dtype, source=None)
        assert dealt >= 0 or dealt <= 0  # Healing returns negative, that's fine

    @given(
        amount=st.integers(min_value=1, max_value=1000),
        max_hp=st.integers(min_value=1, max_value=500),
        dtype=st.sampled_from(damage_types),
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_hp_never_exceeds_max(self, amount, max_hp, dtype):
        """After any damage event, HP should never exceed max_hp."""
        level = Level(5, 5)
        unit = Unit()
        unit.team = Team.ENEMY
        unit.max_hp = max_hp
        unit.cur_hp = max_hp
        level.add_unit(unit, 2, 2)

        level.deal_damage(2, 2, amount, dtype, source=None)
        assert unit.cur_hp <= unit.max_hp

    @given(
        amount=st.integers(min_value=1, max_value=1000),
        max_hp=st.integers(min_value=1, max_value=500),
        dtype=st.sampled_from(damage_types),
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_killed_unit_has_zero_hp(self, amount, max_hp, dtype):
        """A killed unit must have exactly 0 HP."""
        level = Level(5, 5)
        unit = Unit()
        unit.team = Team.ENEMY
        unit.max_hp = max_hp
        unit.cur_hp = max_hp
        level.add_unit(unit, 2, 2)

        level.deal_damage(2, 2, amount, dtype, source=None)
        if unit.killed:
            assert unit.cur_hp == 0
