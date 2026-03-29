"""Tests for the component mastery system."""
from game.constants import Tags, Team
from game.core.level import Level
from game.core.spell_base import Spell
from game.core.unit import Unit
from game.crafting.component_upgrades import (
    ELEMENT_MASTERIES, SHAPE_MASTERIES, MasteryBuff, MasteryTracker,
)


class TestMasteryTracker:
    def test_available_masteries_for_owned_elements(self):
        tracker = MasteryTracker()
        available = tracker.get_available({"Fire"}, set())
        names = [m.name for m in available]
        assert "Fire Mastery I" in names

    def test_no_masteries_without_components(self):
        tracker = MasteryTracker()
        available = tracker.get_available(set(), set())
        assert len(available) == 0

    def test_buy_mastery_advances_level(self):
        tracker = MasteryTracker()
        mastery = ELEMENT_MASTERIES["Fire"][0]
        player = Unit()
        tracker.buy(mastery, player)
        assert tracker.purchased.get("Fire") == 1

    def test_mastery_level_2_available_after_level_1(self):
        tracker = MasteryTracker()
        mastery_1 = ELEMENT_MASTERIES["Fire"][0]
        player = Unit()
        tracker.buy(mastery_1, player)
        available = tracker.get_available({"Fire"}, set())
        names = [m.name for m in available]
        assert "Fire Mastery II" in names
        assert "Fire Mastery I" not in names

    def test_shape_mastery_available(self):
        tracker = MasteryTracker()
        available = tracker.get_available(set(), {"Bolt"})
        names = [m.name for m in available]
        assert "Bolt Mastery I" in names


class TestMasteryBuff:
    def test_mastery_buff_applies_tag_bonus(self):
        mastery = ELEMENT_MASTERIES["Fire"][0]  # +2 fire damage
        player = Unit()
        buff = MasteryBuff(mastery)
        player.apply_buff(buff)
        assert player.tag_bonuses[Tags.Fire]["damage"] == 2

    def test_mastery_affects_spell_damage(self):
        from game.crafting.components import FIRE, BOLT
        from game.crafting.spell_factory import CraftedSpell

        level = Level(9, 9)
        player = Unit()
        player.team = Team.PLAYER
        level.add_unit(player, 1, 1)

        spell = CraftedSpell(FIRE, BOLT)
        player.add_spell(spell)
        base_damage = spell.get_stat("damage")

        mastery = ELEMENT_MASTERIES["Fire"][0]  # +2 fire damage
        buff = MasteryBuff(mastery)
        player.apply_buff(buff)

        boosted_damage = spell.get_stat("damage")
        assert boosted_damage == base_damage + 2


class TestMasteryInGame:
    def test_buy_mastery_through_game(self):
        from game.game.game_state import Game
        g = Game(seed=42)
        g.buy_component("element", "Fire")
        result = g.buy_mastery("Fire Mastery I")
        assert result.get("success")
        # Player should have the mastery buff
        has_mastery = any(isinstance(b, MasteryBuff) for b in g.player.buffs)
        assert has_mastery
