"""Tier 1 monsters — appear in levels 1-2. Basic enemies."""
from __future__ import annotations

from game.constants import Tags, Team
from game.content.monsters.common import SimpleMeleeAttack, SimpleRangedAttack
from game.core.unit import Unit


def make_rat() -> Unit:
    u = Unit()
    u.name = "Giant Rat"
    u.team = Team.ENEMY
    u.max_hp = 8
    u.cur_hp = 8
    u.tags = [Tags.Living]
    u.asset_name = "char/bat"  # Reuse RW2 bat sprite for now
    u.add_spell(SimpleMeleeAttack(damage=3, name="Bite"))
    return u


def make_skeleton() -> Unit:
    u = Unit()
    u.name = "Skeleton"
    u.team = Team.ENEMY
    u.max_hp = 12
    u.cur_hp = 12
    u.tags = [Tags.Undead]
    u.resists[Tags.Dark] = 50
    u.resists[Tags.Holy] = -50
    u.asset_name = "char/skeleton"
    u.add_spell(SimpleMeleeAttack(damage=4, name="Slash"))
    return u


def make_slime() -> Unit:
    u = Unit()
    u.name = "Slime"
    u.team = Team.ENEMY
    u.max_hp = 15
    u.cur_hp = 15
    u.tags = [Tags.Living]
    u.resists[Tags.Physical] = 50
    u.resists[Tags.Fire] = -50
    u.asset_name = "char/slime_green"
    u.add_spell(SimpleMeleeAttack(damage=3, damage_type=Tags.Poison, name="Engulf"))
    return u


def make_goblin_archer() -> Unit:
    u = Unit()
    u.name = "Goblin Archer"
    u.team = Team.ENEMY
    u.max_hp = 10
    u.cur_hp = 10
    u.tags = [Tags.Living]
    u.asset_name = "char/goblin"
    u.add_spell(SimpleRangedAttack(damage=4, spell_range=5, name="Arrow"))
    u.add_spell(SimpleMeleeAttack(damage=2, name="Dagger"))
    return u


def make_imp() -> Unit:
    u = Unit()
    u.name = "Imp"
    u.team = Team.ENEMY
    u.max_hp = 8
    u.cur_hp = 8
    u.flying = True
    u.tags = [Tags.Demon]
    u.resists[Tags.Fire] = 50
    u.resists[Tags.Holy] = -50
    u.asset_name = "char/firebat"
    u.add_spell(SimpleRangedAttack(damage=3, damage_type=Tags.Fire,
                                    spell_range=4, name="Fire Spit"))
    return u


TIER1_SPAWNS = [make_rat, make_skeleton, make_slime, make_goblin_archer, make_imp]
