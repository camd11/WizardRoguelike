"""Tier 3 boss monsters — appear in levels 4-5. Multi-ability bosses with
unique mechanics, modelled on Rift Wizard 2's boss design philosophy."""
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
# Custom spells for boss mechanics
# ---------------------------------------------------------------------------

class DrainLifeAttack(Spell):
    """Melee attack that heals the caster for the damage dealt."""

    def __init__(self, damage: int = 6) -> None:
        self._base_damage = damage
        super().__init__()

    def on_init(self) -> None:
        self.name = "Drain Life"
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
            # Heal caster for damage dealt, capped at missing HP
            heal = min(dealt, self.caster.max_hp - self.caster.cur_hp)
            if heal > 0:
                self.caster.cur_hp += heal
        yield


class WarCrySpell(Spell):
    """Self-buff that grants bonus damage for several turns."""

    def on_init(self) -> None:
        self.name = "War Cry"
        self.damage = 0
        self.range = 0
        self.can_target_self = True
        self.must_target_empty = False
        self.cool_down = 5
        self.tags = [Tags.Physical]

    def get_ai_target(self):
        """Always target self."""
        from game.core.types import Point
        if self.caster and self.can_pay_costs():
            return Point(self.caster.x, self.caster.y)
        return None

    def cast(self, x, y):
        if self.caster:
            buff = WarCryBuff()
            self.caster.apply_buff(buff, duration=4)
        yield


class WarCryBuff(Buff):
    """Grants +4 damage to all attacks for the duration."""

    def on_init(self) -> None:
        self.name = "War Cry"
        self.description = "Damage increased by 4."
        self.color = (255, 100, 50)
        self.global_bonuses["damage"] = 4


class PoisonBiteAttack(Spell):
    """Melee attack that deals damage and applies a poison DOT."""

    def __init__(self, damage: int = 6, poison_damage: int = 3,
                 poison_duration: int = 5) -> None:
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
            # Apply poison DOT to the target
            target = self.level.get_unit_at(x, y)
            if target and target.is_alive():
                poison = PoisonBuff(damage=self._poison_damage)
                target.apply_buff(poison, duration=self._poison_duration)
        yield


class WebShotAttack(Spell):
    """Ranged attack that deals damage and applies a slow (reduced range)."""

    def __init__(self, damage: int = 4, spell_range: int = 5) -> None:
        self._base_damage = damage
        self._range = spell_range
        super().__init__()

    def on_init(self) -> None:
        self.name = "Web Shot"
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


class ChainLightningSpell(Spell):
    """Lightning bolt that chains to 2 additional nearby enemies."""

    def __init__(self, damage: int = 8, spell_range: int = 6,
                 extra_chains: int = 2) -> None:
        self._base_damage = damage
        self._range = spell_range
        self._extra_chains = extra_chains
        super().__init__()

    def on_init(self) -> None:
        self.name = "Chain Lightning"
        self.damage = self._base_damage
        self.damage_type = Tags.Lightning
        self.range = self._range
        self.cool_down = 3
        self.tags = [Tags.Lightning]

    def cast(self, x, y):
        if not self.level or not self.caster:
            yield
            return

        from game.core.types import Point

        dmg = self.get_stat("damage")

        # Hit primary target
        self.level.deal_damage(x, y, dmg, self.damage_type, self)
        yield

        # Chain to additional enemies near the primary target
        hit_positions = {(x, y)}
        chain_origin = Point(x, y)

        for _ in range(self._extra_chains):
            best_target = None
            best_dist = float("inf")

            for unit in self.level.units:
                if unit.team == self.caster.team or not unit.is_alive():
                    continue
                if (unit.x, unit.y) in hit_positions:
                    continue
                pos = Point(unit.x, unit.y)
                dist = chain_origin.distance_to(pos)
                # Chains jump up to 4 tiles
                if dist <= 4.5 and dist < best_dist:
                    best_dist = dist
                    best_target = unit

            if best_target is None:
                break

            self.level.deal_damage(
                best_target.x, best_target.y, dmg, self.damage_type, self
            )
            hit_positions.add((best_target.x, best_target.y))
            chain_origin = Point(best_target.x, best_target.y)
            yield


# ---------------------------------------------------------------------------
# Boss factory functions
# ---------------------------------------------------------------------------

def make_lich_lord() -> Unit:
    """Undead caster boss. Shadow Bolt at range + Drain Life in melee."""
    u = Unit()
    u.name = "Lich Lord"
    u.team = Team.ENEMY
    u.max_hp = 60
    u.cur_hp = 60
    u.tags = [Tags.Undead]
    u.resists[Tags.Dark] = 75
    u.resists[Tags.Holy] = -75
    u.asset_name = "char/bone_wizard"
    u.add_spell(SimpleRangedAttack(damage=10, damage_type=Tags.Dark,
                                    spell_range=7, name="Shadow Bolt"))
    u.add_spell(DrainLifeAttack(damage=6))
    return u


def make_fire_dragon() -> Unit:
    """Fire-breathing dragon boss. Devastating breath + strong claw."""
    u = Unit()
    u.name = "Fire Dragon"
    u.team = Team.ENEMY
    u.max_hp = 80
    u.cur_hp = 80
    u.flying = True
    u.tags = [Tags.Dragon, Tags.Living]
    u.resists[Tags.Fire] = 100
    u.resists[Tags.Ice] = -100
    u.asset_name = "char/fire_drake_armored"
    u.add_spell(SimpleBreathAttack(damage=10, damage_type=Tags.Fire,
                                    radius=4, name="Fire Breath"))
    u.add_spell(SimpleMeleeAttack(damage=8, name="Claw"))
    return u


def make_orc_warlord() -> Unit:
    """Brawler boss. Heavy melee + War Cry self-buff for damage boost."""
    u = Unit()
    u.name = "Orc Warlord"
    u.team = Team.ENEMY
    u.max_hp = 70
    u.cur_hp = 70
    u.tags = [Tags.Living]
    u.resists[Tags.Physical] = 50
    u.asset_name = "char/orc_boss"
    u.add_spell(SimpleMeleeAttack(damage=10, name="Cleave"))
    u.add_spell(WarCrySpell())
    return u


def make_spider_queen() -> Unit:
    """Venomous boss. Poison bite in melee + Web Shot at range."""
    u = Unit()
    u.name = "Spider Queen"
    u.team = Team.ENEMY
    u.max_hp = 60
    u.cur_hp = 60
    u.tags = [Tags.Living]
    u.resists[Tags.Poison] = 75
    u.resists[Tags.Fire] = -50
    u.asset_name = "char/dark_spider_mother"
    u.add_spell(PoisonBiteAttack(damage=6, poison_damage=3, poison_duration=5))
    u.add_spell(WebShotAttack(damage=4, spell_range=5))
    return u


def make_storm_elemental() -> Unit:
    """Elemental boss. Lightning Bolt at range + Chain Lightning for groups."""
    u = Unit()
    u.name = "Storm Elemental"
    u.team = Team.ENEMY
    u.max_hp = 55
    u.cur_hp = 55
    u.tags = [Tags.Construct]
    u.resists[Tags.Lightning] = 100
    u.asset_name = "char/aelf_lightning_lord"
    u.add_spell(SimpleRangedAttack(damage=12, damage_type=Tags.Lightning,
                                    spell_range=6, name="Lightning Bolt"))
    u.add_spell(ChainLightningSpell(damage=8, spell_range=6, extra_chains=2))
    return u


TIER3_SPAWNS = [
    make_lich_lord,
    make_fire_dragon,
    make_orc_warlord,
    make_spider_queen,
    make_storm_elemental,
]
