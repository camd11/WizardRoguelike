"""Tests for consumable items and inventory."""
import pytest

from game.constants import Tags, Team
from game.content.consumables import (
    ConsumableInventory,
    HealingPotion,
    ManaScroll,
    ShieldPotion,
)
from game.core.level import Level
from game.core.spell_base import Spell
from game.core.types import Point
from game.core.unit import Unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class ChargeSpell(Spell):
    """A spell with limited charges for testing ManaScroll."""
    def on_init(self) -> None:
        self.name = "Test Spell"
        self.damage = 5
        self.damage_type = Tags.Fire
        self.range = 5
        self.max_charges = 5
        self.cur_charges = 0  # Depleted
        self.tags = [Tags.Fire]

    def cast(self, x, y):
        yield


def _make_player_on_level() -> tuple[Unit, Level]:
    """Create a player unit placed on a small level."""
    level = Level(9, 9)
    player = Unit()
    player.name = "Player"
    player.team = Team.PLAYER
    player.max_hp = 100
    player.cur_hp = 50  # Damaged
    level.add_unit(player, 4, 4)
    return player, level


# ---------------------------------------------------------------------------
# HealingPotion
# ---------------------------------------------------------------------------

class TestHealingPotion:
    def test_restores_hp(self):
        player, level = _make_player_on_level()
        potion = HealingPotion()
        assert potion.use(player, level)
        assert player.cur_hp == 80  # 50 + 30

    def test_does_not_exceed_max_hp(self):
        player, level = _make_player_on_level()
        player.cur_hp = 90  # Only 10 missing
        potion = HealingPotion()
        assert potion.use(player, level)
        assert player.cur_hp == 100  # Capped at max

    def test_fails_at_full_hp(self):
        player, level = _make_player_on_level()
        player.cur_hp = 100
        potion = HealingPotion()
        assert not potion.use(player, level)
        assert player.cur_hp == 100


# ---------------------------------------------------------------------------
# ManaScroll
# ---------------------------------------------------------------------------

class TestManaScroll:
    def test_restores_charges(self):
        player, level = _make_player_on_level()
        spell = ChargeSpell()
        player.add_spell(spell)
        scroll = ManaScroll()
        assert scroll.use(player, level)
        assert spell.cur_charges == 3

    def test_does_not_exceed_max_charges(self):
        player, level = _make_player_on_level()
        spell = ChargeSpell()
        spell.cur_charges = 4  # Only 1 missing out of 5 max
        player.add_spell(spell)
        scroll = ManaScroll()
        assert scroll.use(player, level)
        assert spell.cur_charges == 5  # Capped at max

    def test_fails_when_all_spells_full(self):
        player, level = _make_player_on_level()
        spell = ChargeSpell()
        spell.cur_charges = 5  # Already full
        player.add_spell(spell)
        scroll = ManaScroll()
        assert not scroll.use(player, level)

    def test_restores_multiple_spells(self):
        player, level = _make_player_on_level()
        s1 = ChargeSpell()
        s1.cur_charges = 0
        s2 = ChargeSpell()
        s2.cur_charges = 1
        player.add_spell(s1)
        player.add_spell(s2)
        scroll = ManaScroll()
        assert scroll.use(player, level)
        assert s1.cur_charges == 3
        assert s2.cur_charges == 4


# ---------------------------------------------------------------------------
# ShieldPotion
# ---------------------------------------------------------------------------

class TestShieldPotion:
    def test_grants_shields(self):
        player, level = _make_player_on_level()
        assert player.shields == 0
        potion = ShieldPotion()
        assert potion.use(player, level)
        assert player.shields == 2

    def test_shield_blocks_damage(self):
        """Shields granted by potion should block incoming damage."""
        player, level = _make_player_on_level()
        player.cur_hp = 100
        potion = ShieldPotion()
        potion.use(player, level)
        dealt = level.deal_damage(4, 4, 10, Tags.Fire, source=None)
        assert dealt == 0
        assert player.shields == 1
        assert player.cur_hp == 100


# ---------------------------------------------------------------------------
# ConsumableInventory
# ---------------------------------------------------------------------------

class TestConsumableInventory:
    def test_max_capacity_is_six(self):
        inv = ConsumableInventory()
        for i in range(6):
            assert inv.add(HealingPotion()), f"Should accept item {i+1}"
        assert not inv.add(HealingPotion()), "Should reject 7th item"
        assert len(inv) == 6

    def test_use_removes_item(self):
        player, level = _make_player_on_level()
        inv = ConsumableInventory()
        inv.add(HealingPotion())
        assert len(inv) == 1
        assert inv.use(0, player, level)
        assert len(inv) == 0

    def test_use_invalid_index_returns_false(self):
        player, level = _make_player_on_level()
        inv = ConsumableInventory()
        assert not inv.use(0, player, level)
        assert not inv.use(-1, player, level)

    def test_failed_use_does_not_remove(self):
        """If the consumable returns False (e.g. heal at full HP), keep it."""
        player, level = _make_player_on_level()
        player.cur_hp = 100  # Full HP
        inv = ConsumableInventory()
        inv.add(HealingPotion())
        assert not inv.use(0, player, level)
        assert len(inv) == 1  # Still in inventory

    def test_get_items_returns_copy(self):
        inv = ConsumableInventory()
        inv.add(HealingPotion())
        items = inv.get_items()
        items.clear()
        assert len(inv) == 1  # Original unchanged
