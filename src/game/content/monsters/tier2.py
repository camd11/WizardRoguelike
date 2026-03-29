"""Tier 2 monsters — appear in levels 3-5. Tougher enemies."""
from __future__ import annotations

from game.constants import Tags, Team
from game.content.monsters.common import (
    SimpleBreathAttack,
    SimpleMeleeAttack,
    SimpleRangedAttack,
)
from game.core.unit import Unit


def make_fire_elemental() -> Unit:
    u = Unit()
    u.name = "Fire Elemental"
    u.team = Team.ENEMY
    u.max_hp = 25
    u.cur_hp = 25
    u.tags = [Tags.Construct]
    u.resists[Tags.Fire] = 100
    u.resists[Tags.Ice] = -100
    u.asset_name = "char/fire_elemental"
    u.add_spell(SimpleRangedAttack(damage=7, damage_type=Tags.Fire,
                                    spell_range=5, name="Fire Bolt"))
    u.add_spell(SimpleMeleeAttack(damage=5, damage_type=Tags.Fire, name="Flame Touch"))
    return u


def make_ice_elemental() -> Unit:
    u = Unit()
    u.name = "Ice Elemental"
    u.team = Team.ENEMY
    u.max_hp = 25
    u.cur_hp = 25
    u.tags = [Tags.Construct]
    u.resists[Tags.Ice] = 100
    u.resists[Tags.Fire] = -100
    u.asset_name = "char/ice_elemental"
    u.add_spell(SimpleRangedAttack(damage=6, damage_type=Tags.Ice,
                                    spell_range=5, name="Frost Bolt"))
    u.add_spell(SimpleMeleeAttack(damage=5, damage_type=Tags.Ice, name="Cold Touch"))
    return u


def make_orc_warrior() -> Unit:
    u = Unit()
    u.name = "Orc Warrior"
    u.team = Team.ENEMY
    u.max_hp = 30
    u.cur_hp = 30
    u.tags = [Tags.Living]
    u.resists[Tags.Physical] = 25
    u.asset_name = "char/orc"
    u.add_spell(SimpleMeleeAttack(damage=8, name="Cleave"))
    return u


def make_dark_mage() -> Unit:
    u = Unit()
    u.name = "Dark Mage"
    u.team = Team.ENEMY
    u.max_hp = 18
    u.cur_hp = 18
    u.tags = [Tags.Living]
    u.resists[Tags.Dark] = 50
    u.resists[Tags.Holy] = -50
    u.asset_name = "char/dark_mage"
    u.add_spell(SimpleRangedAttack(damage=8, damage_type=Tags.Dark,
                                    spell_range=6, name="Shadow Bolt"))
    return u


def make_young_dragon() -> Unit:
    u = Unit()
    u.name = "Young Dragon"
    u.team = Team.ENEMY
    u.max_hp = 40
    u.cur_hp = 40
    u.flying = True
    u.tags = [Tags.Dragon, Tags.Living]
    u.resists[Tags.Fire] = 75
    u.asset_name = "char/fire_drake"
    u.add_spell(SimpleBreathAttack(damage=8, damage_type=Tags.Fire,
                                    radius=3, name="Fire Breath"))
    u.add_spell(SimpleMeleeAttack(damage=6, name="Claw"))
    return u


TIER2_SPAWNS = [make_fire_elemental, make_ice_elemental, make_orc_warrior,
                make_dark_mage, make_young_dragon]
