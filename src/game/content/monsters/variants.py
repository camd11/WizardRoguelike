"""Variant monsters — elemental and special types that add variety.

These sit between tier 1 and tier 2 in power, appearing from difficulty 2
onward. They re-use existing stat ranges but add elemental resistances,
weaknesses, and specialised attacks.
"""
from __future__ import annotations

from game.constants import Tags, Team
from game.content.buffs_common import PoisonBuff
from game.content.monsters.common import (
    SimpleBreathAttack,
    SimpleMeleeAttack,
    SimpleRangedAttack,
)
from game.core.buff import Buff
from game.core.spell_base import Spell
from game.core.unit import Unit


# ---------------------------------------------------------------------------
# Custom spells for variant mechanics
# ---------------------------------------------------------------------------

class PoisonMeleeAttack(Spell):
    """Melee attack that deals damage and applies a poison DOT."""

    def __init__(self, damage: int = 3, damage_type=Tags.Poison,
                 poison_damage: int = 2, poison_duration: int = 4,
                 name: str = "Toxic Engulf") -> None:
        self._base_damage = damage
        self._dtype = damage_type
        self._poison_damage = poison_damage
        self._poison_duration = poison_duration
        self._attack_name = name
        super().__init__()

    def on_init(self) -> None:
        self.name = self._attack_name
        self.damage = self._base_damage
        self.damage_type = self._dtype
        self.range = 1
        self.melee = True
        self.tags = [self._dtype]

    def cast(self, x, y):
        if self.level:
            self.level.deal_damage(
                x, y, self.get_stat("damage"), self.damage_type, self
            )
            target = self.level.get_unit_at(x, y)
            if target and target.is_alive():
                poison = PoisonBuff(damage=self._poison_damage)
                target.apply_buff(poison, duration=self._poison_duration)
        yield


class PoisonBiteAttack(Spell):
    """Melee bite that deals physical damage + poison DOT."""

    def __init__(self, damage: int = 5, poison_damage: int = 2,
                 poison_duration: int = 4) -> None:
        self._base_damage = damage
        self._poison_damage = poison_damage
        self._poison_duration = poison_duration
        super().__init__()

    def on_init(self) -> None:
        self.name = "Poison Bite"
        self.damage = self._base_damage
        self.damage_type = Tags.Physical
        self.range = 1
        self.melee = True
        self.tags = [Tags.Physical, Tags.Poison]

    def cast(self, x, y):
        if self.level:
            self.level.deal_damage(
                x, y, self.get_stat("damage"), self.damage_type, self
            )
            target = self.level.get_unit_at(x, y)
            if target and target.is_alive():
                poison = PoisonBuff(damage=self._poison_damage)
                target.apply_buff(poison, duration=self._poison_duration)
        yield


class WebAttack(Spell):
    """Ranged web that deals minor damage and slows the target."""

    def __init__(self, damage: int = 2, spell_range: int = 5) -> None:
        self._base_damage = damage
        self._range = spell_range
        super().__init__()

    def on_init(self) -> None:
        self.name = "Web"
        self.damage = self._base_damage
        self.damage_type = Tags.Physical
        self.range = self._range
        self.tags = [Tags.Physical]

    def cast(self, x, y):
        if self.level:
            self.level.deal_damage(
                x, y, self.get_stat("damage"), self.damage_type, self
            )
            target = self.level.get_unit_at(x, y)
            if target and target.is_alive():
                web = WebSlowBuff()
                target.apply_buff(web, duration=3)
        yield


class WebSlowBuff(Buff):
    """Webbed — spell range reduced by 2."""

    def on_init(self) -> None:
        self.name = "Webbed"
        self.description = "Webbed. Spell range reduced by 2."
        self.color = (200, 200, 200)
        self.global_bonuses["range"] = -2


class LifeDrainMelee(Spell):
    """Melee dark damage attack that heals caster for damage dealt."""

    def __init__(self, damage: int = 4) -> None:
        self._base_damage = damage
        super().__init__()

    def on_init(self) -> None:
        self.name = "Life Drain"
        self.damage = self._base_damage
        self.damage_type = Tags.Dark
        self.range = 1
        self.melee = True
        self.tags = [Tags.Dark]

    def cast(self, x, y):
        if self.level and self.caster:
            dealt = self.level.deal_damage(
                x, y, self.get_stat("damage"), self.damage_type, self
            )
            heal = min(dealt, self.caster.max_hp - self.caster.cur_hp)
            if heal > 0:
                self.caster.cur_hp += heal
        yield


# ---------------------------------------------------------------------------
# Elemental Variants
# ---------------------------------------------------------------------------

def make_fire_rat() -> Unit:
    """Fire-infused rat. Melee fire bite, resists fire, weak to ice."""
    u = Unit()
    u.name = "Fire Rat"
    u.team = Team.ENEMY
    u.max_hp = 10
    u.cur_hp = 10
    u.tags = [Tags.Living]
    u.resists[Tags.Fire] = 50
    u.resists[Tags.Ice] = -50
    u.asset_name = "char/bat_flame"
    u.add_spell(SimpleMeleeAttack(damage=4, damage_type=Tags.Fire, name="Fire Bite"))
    return u


def make_ice_skeleton() -> Unit:
    """Frost-touched skeleton. Melee ice slash, resists ice, weak to fire."""
    u = Unit()
    u.name = "Ice Skeleton"
    u.team = Team.ENEMY
    u.max_hp = 14
    u.cur_hp = 14
    u.tags = [Tags.Undead]
    u.resists[Tags.Ice] = 50
    u.resists[Tags.Fire] = -50
    u.resists[Tags.Holy] = -50
    u.asset_name = "char/bone_knight"
    u.add_spell(SimpleMeleeAttack(damage=5, damage_type=Tags.Ice, name="Frost Slash"))
    return u


def make_poison_slime() -> Unit:
    """Toxic slime. Melee poison attack with DOT, high poison resist."""
    u = Unit()
    u.name = "Poison Slime"
    u.team = Team.ENEMY
    u.max_hp = 18
    u.cur_hp = 18
    u.tags = [Tags.Living]
    u.resists[Tags.Poison] = 75
    u.asset_name = "char/slime_form"
    u.add_spell(PoisonMeleeAttack(
        damage=3, damage_type=Tags.Poison,
        poison_damage=2, poison_duration=4,
        name="Toxic Engulf",
    ))
    return u


def make_lightning_imp() -> Unit:
    """Copper-skinned imp. Ranged lightning bolt, high lightning resist."""
    u = Unit()
    u.name = "Lightning Imp"
    u.team = Team.ENEMY
    u.max_hp = 10
    u.cur_hp = 10
    u.flying = True
    u.tags = [Tags.Demon]
    u.resists[Tags.Lightning] = 75
    u.asset_name = "char/imp_copper"
    u.add_spell(SimpleRangedAttack(
        damage=5, damage_type=Tags.Lightning,
        spell_range=5, name="Shock Bolt",
    ))
    return u


def make_shadow_goblin() -> Unit:
    """Dark-attuned goblin. Ranged dark arrow + melee dagger, dark resist."""
    u = Unit()
    u.name = "Shadow Goblin"
    u.team = Team.ENEMY
    u.max_hp = 12
    u.cur_hp = 12
    u.tags = [Tags.Living]
    u.resists[Tags.Dark] = 50
    u.asset_name = "char/goblin_cave"
    u.add_spell(SimpleRangedAttack(
        damage=4, damage_type=Tags.Dark,
        spell_range=5, name="Shadow Arrow",
    ))
    u.add_spell(SimpleMeleeAttack(damage=2, name="Dagger"))
    return u


# ---------------------------------------------------------------------------
# Special Types
# ---------------------------------------------------------------------------

def make_skeleton_mage() -> Unit:
    """Undead caster. Ranged dark bolt, weak to holy."""
    u = Unit()
    u.name = "Skeleton Mage"
    u.team = Team.ENEMY
    u.max_hp = 15
    u.cur_hp = 15
    u.tags = [Tags.Undead]
    u.resists[Tags.Dark] = 50
    u.resists[Tags.Holy] = -50
    u.asset_name = "char/bone_wizard"
    u.add_spell(SimpleRangedAttack(
        damage=6, damage_type=Tags.Dark,
        spell_range=6, name="Dark Bolt",
    ))
    return u


def make_goblin_bomber() -> Unit:
    """Goblin demolitionist. Fire bomb breath attack (radius 2)."""
    u = Unit()
    u.name = "Goblin Bomber"
    u.team = Team.ENEMY
    u.max_hp = 10
    u.cur_hp = 10
    u.tags = [Tags.Living]
    u.asset_name = "char/goblin_fire_demolitionist"
    u.add_spell(SimpleBreathAttack(
        damage=5, damage_type=Tags.Fire,
        radius=2, name="Fire Bomb",
    ))
    return u


def make_ghost() -> Unit:
    """Spectral undead. Life drain melee, immune to physical, flying."""
    u = Unit()
    u.name = "Ghost"
    u.team = Team.ENEMY
    u.max_hp = 12
    u.cur_hp = 12
    u.flying = True
    u.tags = [Tags.Undead]
    u.resists[Tags.Physical] = 100
    u.resists[Tags.Dark] = 50
    u.resists[Tags.Holy] = -50
    u.asset_name = "char/aelf_aether_scion"
    u.add_spell(LifeDrainMelee(damage=4))
    return u


def make_giant_spider() -> Unit:
    """Large spider. Poison bite in melee + ranged web to slow targets."""
    u = Unit()
    u.name = "Giant Spider"
    u.team = Team.ENEMY
    u.max_hp = 20
    u.cur_hp = 20
    u.tags = [Tags.Living]
    u.resists[Tags.Poison] = 50
    u.asset_name = "char/dark_spider"
    u.add_spell(PoisonBiteAttack(damage=5, poison_damage=2, poison_duration=4))
    u.add_spell(WebAttack(damage=2, spell_range=5))
    return u


def make_armored_orc() -> Unit:
    """Heavily armored orc. Strong melee slash, high physical resist."""
    u = Unit()
    u.name = "Armored Orc"
    u.team = Team.ENEMY
    u.max_hp = 35
    u.cur_hp = 35
    u.tags = [Tags.Living]
    u.resists[Tags.Physical] = 40
    u.asset_name = "char/orc_armored"
    u.add_spell(SimpleMeleeAttack(damage=7, name="Heavy Slash"))
    return u


def make_cultist() -> Unit:
    """Dual-element caster. Fire bolt and dark bolt at range."""
    u = Unit()
    u.name = "Cultist"
    u.team = Team.ENEMY
    u.max_hp = 14
    u.cur_hp = 14
    u.tags = [Tags.Living]
    u.asset_name = "char/goblin_cultist"
    u.add_spell(SimpleRangedAttack(
        damage=5, damage_type=Tags.Fire,
        spell_range=5, name="Fire Bolt",
    ))
    u.add_spell(SimpleRangedAttack(
        damage=5, damage_type=Tags.Dark,
        spell_range=5, name="Dark Bolt",
    ))
    return u


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

VARIANT_SPAWNS = [
    make_fire_rat,
    make_ice_skeleton,
    make_poison_slime,
    make_lightning_imp,
    make_shadow_goblin,
    make_skeleton_mage,
    make_goblin_bomber,
    make_ghost,
    make_giant_spider,
    make_armored_orc,
    make_cultist,
]
