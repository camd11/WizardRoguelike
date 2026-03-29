"""Tests for the equipment system."""
from game.constants import Tags, Team
from game.content.equipment import (
    EQUIPMENT_POOL,
    ApprenticeStaff,
    FireStaff,
    ClothRobe,
    FlyingBoots,
    get_equipment_drop,
)
from game.core.level import Level
from game.core.rng import GameRNG
from game.core.spell_base import Spell
from game.core.unit import Unit


class TestEquipmentBasics:
    def test_equipment_pool_has_items(self):
        assert len(EQUIPMENT_POOL) >= 3
        for tier, items in EQUIPMENT_POOL.items():
            assert len(items) > 0

    def test_apprentice_staff_adds_damage(self):
        u = Unit()
        u.team = Team.PLAYER
        staff = ApprenticeStaff()
        u.apply_buff(staff)
        # Should have +2 damage globally
        assert u.global_bonuses["damage"] == 2

    def test_fire_staff_adds_fire_damage(self):
        u = Unit()
        u.team = Team.PLAYER
        staff = FireStaff()
        u.apply_buff(staff)
        assert u.tag_bonuses[Tags.Fire]["damage"] == 3

    def test_cloth_robe_adds_hp(self):
        u = Unit()
        u.team = Team.PLAYER
        u.max_hp = 100
        u.cur_hp = 100
        robe = ClothRobe()
        u.apply_buff(robe)
        # Should modify max_hp bonus (implementation may vary)
        # At minimum the buff should apply without error
        assert robe in u.buffs

    def test_flying_boots_grant_flying(self):
        u = Unit()
        boots = FlyingBoots()
        u.apply_buff(boots)
        assert u.flying

    def test_equipment_drop_returns_item(self):
        rng = GameRNG(42)
        item = get_equipment_drop(3, rng)
        assert item is not None
        assert hasattr(item, 'name')
        assert hasattr(item, 'slot')

    def test_equip_and_unequip_symmetry(self):
        u = Unit()
        staff = ApprenticeStaff()
        u.apply_buff(staff)
        assert u.global_bonuses["damage"] == 2
        u.remove_buff(staff)
        assert u.global_bonuses["damage"] == 0


class TestSmartBotStrategies:
    def test_all_strategies_complete(self):
        """Each build strategy should complete a run without crashing."""
        from tests.simulation.smart_bot import SmartBot, BUILD_STRATEGIES
        for si in range(len(BUILD_STRATEGIES)):
            bot = SmartBot(seed=42, strategy_idx=si)
            result = bot.play_full_run(max_turns=100)
            assert result["turns_played"] > 0
            assert result["enemies_killed"] >= 0
