"""Integration tests for piercing damage mechanics."""
import math

import pytest

from game.constants import Tags, Team
from game.core.level import Level
from game.core.unit import Unit
from game.crafting.components import (
    ARCANE,
    BOLT,
    FIRE,
    PIERCING,
)
from game.crafting.spell_factory import CraftedSpell


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_combat(player_x: int = 1, player_y: int = 4,
                  enemy_x: int = 5, enemy_y: int = 4,
                  enemy_resist_tag=None, resist_pct: int = 0
                  ) -> tuple[Level, Unit, Unit]:
    """Create a level with player and enemy. Optionally give enemy resistance."""
    level = Level(9, 9)
    player = Unit()
    player.name = "Player"
    player.team = Team.PLAYER
    player.max_hp = 100
    player.cur_hp = 100
    level.add_unit(player, player_x, player_y)

    enemy = Unit()
    enemy.name = "Resistant Target"
    enemy.team = Team.ENEMY
    enemy.max_hp = 100
    enemy.cur_hp = 100
    if enemy_resist_tag is not None:
        enemy.resists[enemy_resist_tag] = resist_pct
    level.add_unit(enemy, enemy_x, enemy_y)

    return level, player, enemy


def _cast_and_drain(level: Level, player: Unit, spell: CraftedSpell,
                    x: int, y: int) -> None:
    """Cast a spell and drain all animations."""
    level.act_cast(player, spell, x, y)
    while level.advance_spells():
        pass


# ---------------------------------------------------------------------------
# get_pierce_pct unit tests
# ---------------------------------------------------------------------------

class TestGetPiercePct:
    def test_fire_bolt_no_pierce(self):
        spell = CraftedSpell(FIRE, BOLT)
        assert spell.get_pierce_pct() == 0

    def test_piercing_modifier_gives_50(self):
        spell = CraftedSpell(FIRE, BOLT, [PIERCING])
        assert spell.get_pierce_pct() == 50

    def test_arcane_element_gives_25(self):
        spell = CraftedSpell(ARCANE, BOLT)
        assert spell.get_pierce_pct() == 25

    def test_arcane_plus_piercing_gives_75(self):
        spell = CraftedSpell(ARCANE, BOLT, [PIERCING])
        assert spell.get_pierce_pct() == 75

    def test_pierce_capped_at_90(self):
        """Even with stacking, pierce should never exceed 90%."""
        spell = CraftedSpell(ARCANE, BOLT, [PIERCING])
        assert spell.get_pierce_pct() <= 90


# ---------------------------------------------------------------------------
# Piercing modifier deals more damage to resistant target
# ---------------------------------------------------------------------------

class TestPiercingDamage:
    def test_piercing_vs_resistant_target(self):
        """A Piercing Fire Bolt should deal more damage than a plain Fire Bolt
        against a fire-resistant enemy."""
        # Plain Fire Bolt
        level1, player1, enemy1 = _setup_combat(
            enemy_resist_tag=Tags.Fire, resist_pct=80
        )
        plain = CraftedSpell(FIRE, BOLT)
        player1.add_spell(plain)
        _cast_and_drain(level1, player1, plain, 5, 4)
        damage_plain = 100 - enemy1.cur_hp

        # Piercing Fire Bolt
        level2, player2, enemy2 = _setup_combat(
            enemy_resist_tag=Tags.Fire, resist_pct=80
        )
        piercing = CraftedSpell(FIRE, BOLT, [PIERCING])
        player2.add_spell(piercing)
        _cast_and_drain(level2, player2, piercing, 5, 4)
        damage_piercing = 100 - enemy2.cur_hp

        assert damage_piercing > damage_plain, (
            f"Piercing ({damage_piercing}) should deal more than plain ({damage_plain}) "
            f"vs 80% Fire resist"
        )

    def test_arcane_pierces_25_pct_resistance(self):
        """Arcane element innately pierces 25% of resistance.

        With 80% Arcane resistance and 25% pierce:
          effective_resist = 80 * (100 - 25) / 100 = 60
          damage = ceil(12 * (100 - 60) / 100) = ceil(4.8) = 5
        Without pierce (plain Fire at 80% resist):
          damage = ceil(9 * (100 - 80) / 100) = ceil(1.8) = 2
        """
        level, player, enemy = _setup_combat(
            enemy_resist_tag=Tags.Arcane, resist_pct=80
        )
        spell = CraftedSpell(ARCANE, BOLT)
        player.add_spell(spell)
        _cast_and_drain(level, player, spell, 5, 4)

        # Arcane base damage = 12
        # effective_resist = int(80 * (100 - 25) / 100) = int(80 * 0.75) = 60
        # damage = ceil(12 * (100 - 60) / 100) = ceil(4.8) = 5
        expected_resist = max(0, int(80 * (100 - 25) / 100))  # 60
        expected_damage = math.ceil(ARCANE.base_damage * (100 - expected_resist) / 100)
        actual_damage = 100 - enemy.cur_hp
        assert actual_damage == expected_damage, (
            f"Expected {expected_damage} damage with 25% pierce vs 80% resist, "
            f"got {actual_damage}"
        )

    def test_piercing_plus_arcane_stacks(self):
        """Piercing modifier (50%) + Arcane element (25%) = 75% pierce.

        With 100% Arcane resist and 75% pierce:
          effective_resist = int(100 * (100 - 75) / 100) = 25
          damage = ceil(12 * (100 - 25) / 100) = ceil(9.0) = 9
        """
        level, player, enemy = _setup_combat(
            enemy_resist_tag=Tags.Arcane, resist_pct=100
        )
        spell = CraftedSpell(ARCANE, BOLT, [PIERCING])
        player.add_spell(spell)
        _cast_and_drain(level, player, spell, 5, 4)

        expected_resist = max(0, int(100 * (100 - 75) / 100))  # 25
        expected_damage = math.ceil(ARCANE.base_damage * (100 - expected_resist) / 100)
        actual_damage = 100 - enemy.cur_hp
        assert actual_damage == expected_damage, (
            f"Expected {expected_damage} with 75% pierce vs 100% resist, "
            f"got {actual_damage}"
        )

    def test_no_pierce_against_zero_resist(self):
        """Piercing has no effect when the target has no resistance."""
        level1, player1, enemy1 = _setup_combat()
        plain = CraftedSpell(FIRE, BOLT)
        player1.add_spell(plain)
        _cast_and_drain(level1, player1, plain, 5, 4)
        dmg_plain = 100 - enemy1.cur_hp

        level2, player2, enemy2 = _setup_combat()
        piercing = CraftedSpell(FIRE, BOLT, [PIERCING])
        player2.add_spell(piercing)
        _cast_and_drain(level2, player2, piercing, 5, 4)
        dmg_pierce = 100 - enemy2.cur_hp

        assert dmg_plain == dmg_pierce, (
            "Piercing should have no effect against 0% resistance"
        )
