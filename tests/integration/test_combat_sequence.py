"""Integration tests: full combat sequences using crafted spells."""
import pytest

from game.constants import Tags, Team
from game.core.level import Level
from game.core.unit import Unit
from game.crafting.components import FIRE, ICE, BOLT, BURST, TOUCH, EMPOWERED
from game.crafting.spell_factory import CraftedSpell


class TestCraftCastKill:
    """Full cycle: craft spell → cast at enemy → verify damage → verify death."""

    def test_fire_bolt_kills_weak_enemy(self):
        level = Level(9, 9)
        player = Unit()
        player.team = Team.PLAYER
        player.max_hp = 100
        player.cur_hp = 100
        level.add_unit(player, 1, 4)

        enemy = Unit()
        enemy.team = Team.ENEMY
        enemy.max_hp = 8
        enemy.cur_hp = 8
        level.add_unit(enemy, 5, 4)

        spell = CraftedSpell(FIRE, BOLT)
        player.add_spell(spell)

        # Cast
        assert spell.can_cast(5, 4)
        assert spell.can_pay_costs()
        level.act_cast(player, spell, 5, 4)

        # Drain spell animations
        while level.advance_spells():
            pass

        assert not enemy.is_alive()

    def test_empowered_ice_burst_hits_cluster(self):
        level = Level(15, 15)
        player = Unit()
        player.team = Team.PLAYER
        player.max_hp = 100
        player.cur_hp = 100
        level.add_unit(player, 1, 7)

        enemies = []
        for x, y in [(7, 7), (8, 7), (7, 8), (8, 8)]:
            e = Unit()
            e.team = Team.ENEMY
            e.max_hp = 50
            e.cur_hp = 50
            level.add_unit(e, x, y)
            enemies.append(e)

        spell = CraftedSpell(ICE, BURST, [EMPOWERED])
        player.add_spell(spell)
        level.act_cast(player, spell, 7, 7)

        while level.advance_spells():
            pass

        damaged = sum(1 for e in enemies if e.cur_hp < 50)
        assert damaged >= 2  # Burst should hit multiple

    def test_touch_spell_melee_combat(self):
        level = Level(9, 9)
        player = Unit()
        player.team = Team.PLAYER
        player.max_hp = 100
        player.cur_hp = 100
        level.add_unit(player, 4, 4)

        enemy = Unit()
        enemy.team = Team.ENEMY
        enemy.max_hp = 8
        enemy.cur_hp = 8
        level.add_unit(enemy, 5, 4)

        spell = CraftedSpell(FIRE, TOUCH)
        player.add_spell(spell)
        level.act_cast(player, spell, 5, 4)

        while level.advance_spells():
            pass

        assert not enemy.is_alive()


class TestBuffAppliedDuringCombat:
    def test_fire_bolt_applies_burn(self):
        """Fire bolt should apply burn DOT on hit."""
        level = Level(9, 9)
        player = Unit()
        player.team = Team.PLAYER
        player.max_hp = 100
        player.cur_hp = 100
        level.add_unit(player, 1, 4)

        enemy = Unit()
        enemy.team = Team.ENEMY
        enemy.max_hp = 100
        enemy.cur_hp = 100
        level.add_unit(enemy, 5, 4)

        spell = CraftedSpell(FIRE, BOLT)
        player.add_spell(spell)
        level.act_cast(player, spell, 5, 4)

        while level.advance_spells():
            pass

        # Enemy should have a Burn buff
        has_burn = any(b.name in ("Burn", "Burning") for b in enemy.buffs)
        assert has_burn, f"Expected burn buff, got: {enemy.buffs}"
