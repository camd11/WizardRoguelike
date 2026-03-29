"""Tests for the spell synergy system."""
from game.constants import Tags, Team
from game.core.level import Level
from game.core.unit import Unit
from game.crafting.synergies import SynergyTracker, ALL_SYNERGIES


class TestSynergyActivation:
    def test_no_synergies_with_single_element(self):
        tracker = SynergyTracker()
        player = Unit()
        new = tracker.check_synergies({"Fire"}, player)
        assert len(new) == 0

    def test_steam_power_activates(self):
        tracker = SynergyTracker()
        player = Unit()
        new = tracker.check_synergies({"Fire", "Ice"}, player)
        assert "Steam Power" in new

    def test_tempest_activates(self):
        tracker = SynergyTracker()
        player = Unit()
        new = tracker.check_synergies({"Lightning", "Dark"}, player)
        assert "Tempest" in new

    def test_blight_activates(self):
        tracker = SynergyTracker()
        player = Unit()
        new = tracker.check_synergies({"Nature", "Poison"}, player)
        assert "Blight" in new

    def test_synergy_not_duplicated(self):
        tracker = SynergyTracker()
        player = Unit()
        tracker.check_synergies({"Fire", "Ice"}, player)
        new = tracker.check_synergies({"Fire", "Ice"}, player)
        assert len(new) == 0  # Already active

    def test_synergy_applies_buff(self):
        tracker = SynergyTracker()
        player = Unit()
        tracker.check_synergies({"Fire", "Ice"}, player)
        # Steam Power grants +2 damage globally
        assert player.global_bonuses["damage"] == 2

    def test_multiple_synergies(self):
        tracker = SynergyTracker()
        player = Unit()
        new = tracker.check_synergies({"Fire", "Ice", "Lightning", "Dark"}, player)
        assert "Steam Power" in new
        assert "Tempest" in new

    def test_get_active_synergies(self):
        tracker = SynergyTracker()
        player = Unit()
        tracker.check_synergies({"Fire", "Ice"}, player)
        active = tracker.get_active_synergies()
        assert len(active) == 1
        assert active[0].name == "Steam Power"


class TestSynergyInGame:
    def test_buy_triggers_synergy(self):
        from game.game.game_state import Game
        g = Game(seed=42)
        g.buy_component("element", "Fire")
        r = g.buy_component("element", "Ice")
        assert "Steam Power" in r.get("synergies_activated", [])
