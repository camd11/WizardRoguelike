"""Special monsters with unique mechanics — auras, summoning, explosions,
shields/regen, multi-attack, teleporting, debuffs, and swarms.

These add tactical variety beyond the standard attack-and-resist roster.
"""
from __future__ import annotations

import random

from game.constants import Tags, Team
from game.content.buffs_common import BlindBuff, PoisonBuff, RegenerationBuff, ShieldBuff
from game.content.monsters.common import SimpleMeleeAttack, SimpleRangedAttack
from game.core.buff import Buff
from game.core.events import EventOnDeath
from game.core.shapes import get_burst_points
from game.core.spell_base import Spell
from game.core.types import Point
from game.core.unit import Unit


# ---------------------------------------------------------------------------
# Aura buffs
# ---------------------------------------------------------------------------

class FireAuraBuff(Buff):
    """Deals fire damage to adjacent enemies each turn."""

    def __init__(self, damage: int = 3) -> None:
        self._aura_dmg = damage
        super().__init__()

    def on_init(self) -> None:
        self.name = "Fire Aura"
        self.description = f"Deals {self._aura_dmg} fire damage to adjacent enemies."
        self.color = (255, 100, 20)

    def on_advance(self) -> None:
        if not self.owner or not self.owner.level:
            return
        level = self.owner.level
        origin = Point(self.owner.x, self.owner.y)
        points = get_burst_points(level, origin, 1, ignore_walls=False)
        for p in points:
            if p.x == origin.x and p.y == origin.y:
                continue
            unit = level.get_unit_at(p.x, p.y)
            if unit and unit.is_alive() and unit.team != self.owner.team:
                level.deal_damage(p.x, p.y, self._aura_dmg, Tags.Fire, self)


class IceAuraBuff(Buff):
    """Deals ice damage to adjacent enemies and slows them each turn."""

    def __init__(self, damage: int = 2) -> None:
        self._aura_dmg = damage
        super().__init__()

    def on_init(self) -> None:
        self.name = "Ice Aura"
        self.description = f"Deals {self._aura_dmg} ice damage and slows adjacent enemies."
        self.color = (100, 200, 255)

    def on_advance(self) -> None:
        if not self.owner or not self.owner.level:
            return
        level = self.owner.level
        origin = Point(self.owner.x, self.owner.y)
        points = get_burst_points(level, origin, 1, ignore_walls=False)
        for p in points:
            if p.x == origin.x and p.y == origin.y:
                continue
            unit = level.get_unit_at(p.x, p.y)
            if unit and unit.is_alive() and unit.team != self.owner.team:
                level.deal_damage(p.x, p.y, self._aura_dmg, Tags.Ice, self)
                slow = IceSlowBuff()
                unit.apply_buff(slow, duration=2)


class IceSlowBuff(Buff):
    """Chilled — spell range reduced by 2."""

    def on_init(self) -> None:
        self.name = "Chilled"
        self.description = "Chilled. Spell range reduced by 2."
        self.color = (150, 220, 255)
        self.global_bonuses["range"] = -2


# ---------------------------------------------------------------------------
# Summoner spells
# ---------------------------------------------------------------------------

class SummonSkeletonSpell(Spell):
    """Summons a skeleton minion near the caster every few turns."""

    def __init__(self, cooldown: int = 4) -> None:
        self._cd = cooldown
        super().__init__()

    def on_init(self) -> None:
        self.name = "Raise Skeleton"
        self.damage = 0
        self.range = 0
        self.can_target_self = True
        self.must_target_empty = False
        self.cool_down = self._cd
        self.tags = [Tags.Dark]

    def get_ai_target(self):
        if self.caster and self.can_pay_costs():
            return Point(self.caster.x, self.caster.y)
        return None

    def cast(self, x, y):
        if not self.caster or not self.level:
            yield
            return

        # Find an empty adjacent tile
        spawn_point = self._find_spawn_point()
        if spawn_point:
            minion = _make_summoned_skeleton()
            self.level.add_unit(minion, spawn_point.x, spawn_point.y)
        yield

    def _find_spawn_point(self) -> Point | None:
        if not self.caster or not self.level:
            return None
        ox, oy = self.caster.x, self.caster.y
        candidates = []
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = ox + dx, oy + dy
                if self.level.in_bounds(nx, ny):
                    tile = self.level.tiles[nx][ny]
                    if tile.is_floor and tile.unit is None:
                        candidates.append(Point(nx, ny))
        if candidates:
            return random.choice(candidates)
        return None


def _make_summoned_skeleton() -> Unit:
    """Weak skeleton minion spawned by Necromancer."""
    u = Unit()
    u.name = "Skeleton Minion"
    u.team = Team.ENEMY
    u.max_hp = 6
    u.cur_hp = 6
    u.tags = [Tags.Undead]
    u.resists[Tags.Dark] = 50
    u.resists[Tags.Holy] = -50
    u.asset_name = "char/bone_knight"
    u.turns_to_death = 8
    u.add_spell(SimpleMeleeAttack(damage=3, name="Slash"))
    return u


class SummonSpidersSpell(Spell):
    """Summons 2 small spiders near the caster."""

    def __init__(self, cooldown: int = 5) -> None:
        self._cd = cooldown
        super().__init__()

    def on_init(self) -> None:
        self.name = "Spawn Brood"
        self.damage = 0
        self.range = 0
        self.can_target_self = True
        self.must_target_empty = False
        self.cool_down = self._cd
        self.tags = [Tags.Poison]

    def get_ai_target(self):
        if self.caster and self.can_pay_costs():
            return Point(self.caster.x, self.caster.y)
        return None

    def cast(self, x, y):
        if not self.caster or not self.level:
            yield
            return

        spawn_points = self._find_spawn_points(2)
        for sp in spawn_points:
            minion = _make_small_spider()
            self.level.add_unit(minion, sp.x, sp.y)
        yield

    def _find_spawn_points(self, count: int) -> list[Point]:
        if not self.caster or not self.level:
            return []
        ox, oy = self.caster.x, self.caster.y
        candidates = []
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = ox + dx, oy + dy
                if self.level.in_bounds(nx, ny):
                    tile = self.level.tiles[nx][ny]
                    if tile.is_floor and tile.unit is None:
                        candidates.append(Point(nx, ny))
        random.shuffle(candidates)
        return candidates[:count]


def _make_small_spider() -> Unit:
    """Weak spider minion spawned by Hive Mother."""
    u = Unit()
    u.name = "Spiderling"
    u.team = Team.ENEMY
    u.max_hp = 4
    u.cur_hp = 4
    u.tags = [Tags.Living]
    u.asset_name = "char/dark_spider"
    u.turns_to_death = 6
    u.add_spell(SimpleMeleeAttack(damage=2, damage_type=Tags.Poison, name="Bite"))
    return u


# ---------------------------------------------------------------------------
# Explosive (death) buffs
# ---------------------------------------------------------------------------

class DeathExplosionBuff(Buff):
    """Explodes on death, dealing AOE damage in a radius."""

    def __init__(self, damage: int = 8, radius: int = 2,
                 damage_type=Tags.Fire) -> None:
        self._explode_dmg = damage
        self._explode_radius = radius
        self._explode_dtype = damage_type
        super().__init__()

    def on_init(self) -> None:
        self.name = "Volatile"
        self.description = (f"Explodes on death for {self._explode_dmg} "
                            f"{self._explode_dtype.name} damage in radius "
                            f"{self._explode_radius}.")
        self.color = (255, 60, 20)
        self.owner_triggers[EventOnDeath] = self._on_death

    def _on_death(self, event) -> None:
        if not self.owner or not self.owner.level:
            return
        level = self.owner.level
        origin = Point(self.owner.x, self.owner.y)
        points = get_burst_points(level, origin, self._explode_radius,
                                  ignore_walls=False)
        for p in points:
            if p.x == origin.x and p.y == origin.y:
                continue
            unit = level.get_unit_at(p.x, p.y)
            if unit and unit.is_alive():
                level.deal_damage(p.x, p.y, self._explode_dmg,
                                  self._explode_dtype, self)


# ---------------------------------------------------------------------------
# Teleport (blink) buff
# ---------------------------------------------------------------------------

class BlinkBuff(Buff):
    """Teleports the owner to a random floor tile every N turns."""

    def __init__(self, interval: int = 3) -> None:
        self._interval = interval
        self._turn_counter = 0
        super().__init__()

    def on_init(self) -> None:
        self.name = "Phase Shift"
        self.description = f"Teleports every {self._interval} turns."
        self.color = (180, 80, 255)

    def on_advance(self) -> None:
        self._turn_counter += 1
        if self._turn_counter < self._interval:
            return
        self._turn_counter = 0

        if not self.owner or not self.owner.level:
            return
        level = self.owner.level

        # Collect all walkable empty floor tiles
        candidates = []
        for x in range(level.width):
            for y in range(level.height):
                tile = level.tiles[x][y]
                if tile.is_floor and tile.unit is None:
                    candidates.append(Point(x, y))

        if candidates:
            target = random.choice(candidates)
            level.teleport(self.owner, target.x, target.y)


# ---------------------------------------------------------------------------
# Debuff-on-hit spells
# ---------------------------------------------------------------------------

class PoisonBiteSpecial(Spell):
    """Melee attack that deals damage and applies a poison DOT."""

    def __init__(self, damage: int = 2, poison_damage: int = 3,
                 poison_duration: int = 4) -> None:
        self._base_damage = damage
        self._poison_damage = poison_damage
        self._poison_duration = poison_duration
        super().__init__()

    def on_init(self) -> None:
        self.name = "Plague Bite"
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


class BlindingBoltSpell(Spell):
    """Ranged dark bolt that applies BlindBuff on hit."""

    def __init__(self, damage: int = 6, spell_range: int = 6) -> None:
        self._base_damage = damage
        self._range = spell_range
        super().__init__()

    def on_init(self) -> None:
        self.name = "Mind Blast"
        self.damage = self._base_damage
        self.damage_type = Tags.Dark
        self.range = self._range
        self.tags = [Tags.Dark]

    def cast(self, x, y):
        if self.level:
            self.level.deal_damage(
                x, y, self.get_stat("damage"), self.damage_type, self
            )
            target = self.level.get_unit_at(x, y)
            if target and target.is_alive():
                blind = BlindBuff()
                target.apply_buff(blind, duration=2)
        yield


class CurseBoltSpell(Spell):
    """Ranged holy bolt that applies a damage-reducing curse."""

    def __init__(self, damage: int = 4, spell_range: int = 6) -> None:
        self._base_damage = damage
        self._range = spell_range
        super().__init__()

    def on_init(self) -> None:
        self.name = "Curse"
        self.damage = self._base_damage
        self.damage_type = Tags.Holy
        self.range = self._range
        self.tags = [Tags.Holy]

    def cast(self, x, y):
        if self.level:
            self.level.deal_damage(
                x, y, self.get_stat("damage"), self.damage_type, self
            )
            target = self.level.get_unit_at(x, y)
            if target and target.is_alive():
                curse = CurseDebuff()
                target.apply_buff(curse, duration=3)
        yield


class CurseDebuff(Buff):
    """Cursed — all damage dealt reduced by 3."""

    def on_init(self) -> None:
        self.name = "Cursed"
        self.description = "Cursed. All damage reduced by 3."
        self.color = (120, 20, 120)
        self.global_bonuses["damage"] = -3


# ---------------------------------------------------------------------------
# Monster factory functions
# ---------------------------------------------------------------------------

# --- Aura Monsters ---

def make_flame_acolyte() -> Unit:
    """Fire aura melee fighter. Burns adjacent enemies each turn."""
    u = Unit()
    u.name = "Flame Acolyte"
    u.team = Team.ENEMY
    u.max_hp = 20
    u.cur_hp = 20
    u.tags = [Tags.Living]
    u.resists[Tags.Fire] = 50
    u.asset_name = "char/goblin_cultist"
    u.add_spell(SimpleMeleeAttack(damage=4, damage_type=Tags.Fire, name="Flame Strike"))
    u.apply_buff(FireAuraBuff(damage=3))
    return u


def make_frost_wraith() -> Unit:
    """Flying ice aura + ranged ice bolt. Chills adjacent enemies."""
    u = Unit()
    u.name = "Frost Wraith"
    u.team = Team.ENEMY
    u.max_hp = 18
    u.cur_hp = 18
    u.flying = True
    u.tags = [Tags.Undead]
    u.resists[Tags.Ice] = 75
    u.resists[Tags.Fire] = -50
    u.asset_name = "char/aelf_aether_scion"
    u.add_spell(SimpleRangedAttack(damage=5, damage_type=Tags.Ice,
                                    spell_range=5, name="Ice Bolt"))
    u.apply_buff(IceAuraBuff(damage=2))
    return u


# --- Summoner Monsters ---

def make_necromancer() -> Unit:
    """Summons skeleton minions and fires shadow bolts."""
    u = Unit()
    u.name = "Necromancer"
    u.team = Team.ENEMY
    u.max_hp = 22
    u.cur_hp = 22
    u.tags = [Tags.Living]
    u.resists[Tags.Dark] = 50
    u.resists[Tags.Holy] = -50
    u.asset_name = "char/bone_wizard"
    u.add_spell(SimpleRangedAttack(damage=5, damage_type=Tags.Dark,
                                    spell_range=6, name="Shadow Bolt"))
    u.add_spell(SummonSkeletonSpell(cooldown=4))
    return u


def make_hive_mother() -> Unit:
    """Spawns spiderlings and bites with poison."""
    u = Unit()
    u.name = "Hive Mother"
    u.team = Team.ENEMY
    u.max_hp = 30
    u.cur_hp = 30
    u.tags = [Tags.Living]
    u.resists[Tags.Poison] = 75
    u.asset_name = "char/dark_spider_mother"
    u.add_spell(SimpleMeleeAttack(damage=4, damage_type=Tags.Poison, name="Poison Bite"))
    u.add_spell(SummonSpidersSpell(cooldown=5))
    return u


# --- Explosive Monsters ---

def make_bomb_beetle() -> Unit:
    """Fragile melee bug that explodes on death for fire AOE."""
    u = Unit()
    u.name = "Bomb Beetle"
    u.team = Team.ENEMY
    u.max_hp = 8
    u.cur_hp = 8
    u.tags = [Tags.Living]
    u.resists[Tags.Fire] = 50
    u.asset_name = "char/goblin_cannon_ball"
    u.add_spell(SimpleMeleeAttack(damage=3, name="Headbutt"))
    u.apply_buff(DeathExplosionBuff(damage=8, radius=2, damage_type=Tags.Fire))
    return u


def make_unstable_elemental() -> Unit:
    """Ranged arcane attacker that explodes on death for arcane AOE."""
    u = Unit()
    u.name = "Unstable Elemental"
    u.team = Team.ENEMY
    u.max_hp = 12
    u.cur_hp = 12
    u.tags = [Tags.Construct]
    u.resists[Tags.Arcane] = 50
    u.asset_name = "char/aelf_aether_prism"
    u.add_spell(SimpleRangedAttack(damage=4, damage_type=Tags.Arcane,
                                    spell_range=5, name="Arcane Bolt"))
    u.apply_buff(DeathExplosionBuff(damage=10, radius=1, damage_type=Tags.Arcane))
    return u


# --- Shield/Regen Monsters ---

def make_stone_golem() -> Unit:
    """Tanky golem with physical resist and regeneration."""
    u = Unit()
    u.name = "Stone Golem"
    u.team = Team.ENEMY
    u.max_hp = 40
    u.cur_hp = 40
    u.tags = [Tags.Construct]
    u.resists[Tags.Physical] = 50
    u.asset_name = "char/orc_anvil"
    u.add_spell(SimpleMeleeAttack(damage=10, name="Slam"))
    u.apply_buff(RegenerationBuff(heal=3))
    return u


def make_shield_guardian() -> Unit:
    """Melee defender that starts with 3 shields."""
    u = Unit()
    u.name = "Shield Guardian"
    u.team = Team.ENEMY
    u.max_hp = 25
    u.cur_hp = 25
    u.shields = 3
    u.tags = [Tags.Construct]
    u.resists[Tags.Physical] = 25
    u.asset_name = "char/aesir_immortal"
    u.add_spell(SimpleMeleeAttack(damage=6, name="Shield Bash"))
    return u


# --- Multi-Attack Monsters ---

def make_blade_dancer() -> Unit:
    """Fast melee fighter with two attacks per turn."""
    u = Unit()
    u.name = "Blade Dancer"
    u.team = Team.ENEMY
    u.max_hp = 15
    u.cur_hp = 15
    u.tags = [Tags.Living]
    u.asset_name = "char/aelf_elite"
    u.add_spell(SimpleMeleeAttack(damage=4, name="Left Slash"))
    u.add_spell(SimpleMeleeAttack(damage=4, name="Right Slash"))
    return u


def make_arcane_turret() -> Unit:
    """Stationary turret that fires 2 arcane bolts per turn."""
    u = Unit()
    u.name = "Arcane Turret"
    u.team = Team.ENEMY
    u.max_hp = 20
    u.cur_hp = 20
    u.stationary = True
    u.tags = [Tags.Construct]
    u.resists[Tags.Arcane] = 50
    u.asset_name = "char/dark_runestone"
    u.add_spell(SimpleRangedAttack(damage=5, damage_type=Tags.Arcane,
                                    spell_range=7, name="Arcane Bolt I"))
    u.add_spell(SimpleRangedAttack(damage=5, damage_type=Tags.Arcane,
                                    spell_range=7, name="Arcane Bolt II"))
    return u


# --- Phase/Teleport Monsters ---

def make_blink_fox() -> Unit:
    """Elusive melee attacker that teleports every 3 turns."""
    u = Unit()
    u.name = "Blink Fox"
    u.team = Team.ENEMY
    u.max_hp = 10
    u.cur_hp = 10
    u.tags = [Tags.Living]
    u.asset_name = "char/accursed_cat"
    u.add_spell(SimpleMeleeAttack(damage=5, name="Phase Claw"))
    u.apply_buff(BlinkBuff(interval=3))
    return u


# --- Debuff Monsters ---

def make_plague_rat() -> Unit:
    """Weak rat whose bite inflicts lingering poison."""
    u = Unit()
    u.name = "Plague Rat"
    u.team = Team.ENEMY
    u.max_hp = 10
    u.cur_hp = 10
    u.tags = [Tags.Living]
    u.asset_name = "char/bat_toxic"
    u.add_spell(PoisonBiteSpecial(damage=2, poison_damage=3, poison_duration=4))
    return u


def make_mind_flayer() -> Unit:
    """Ranged dark caster that blinds targets on hit."""
    u = Unit()
    u.name = "Mind Flayer"
    u.team = Team.ENEMY
    u.max_hp = 25
    u.cur_hp = 25
    u.tags = [Tags.Demon]
    u.resists[Tags.Dark] = 50
    u.asset_name = "char/3x3_mind_devourer"
    u.add_spell(BlindingBoltSpell(damage=6, spell_range=6))
    return u


def make_curse_priest() -> Unit:
    """Ranged holy caster that curses targets, reducing their damage."""
    u = Unit()
    u.name = "Curse Priest"
    u.team = Team.ENEMY
    u.max_hp = 18
    u.cur_hp = 18
    u.tags = [Tags.Living]
    u.resists[Tags.Holy] = 50
    u.resists[Tags.Dark] = -50
    u.asset_name = "char/dark_priest"
    u.add_spell(CurseBoltSpell(damage=4, spell_range=6))
    return u


# --- Swarm Monster ---

def make_rat_swarm() -> Unit:
    """A single rat from the swarm. Always spawn 3 via make_rat_swarm_group()."""
    u = Unit()
    u.name = "Rat Swarm"
    u.team = Team.ENEMY
    u.max_hp = 5
    u.cur_hp = 5
    u.tags = [Tags.Living]
    u.asset_name = "char/bat"
    u.add_spell(SimpleMeleeAttack(damage=2, name="Gnaw"))
    return u


def make_rat_swarm_group() -> list[Unit]:
    """Create a group of 3 swarm rats. Caller should place them nearby."""
    return [make_rat_swarm() for _ in range(3)]


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

SPECIAL_SPAWNS = [
    make_flame_acolyte,
    make_frost_wraith,
    make_necromancer,
    make_hive_mother,
    make_bomb_beetle,
    make_unstable_elemental,
    make_stone_golem,
    make_shield_guardian,
    make_blade_dancer,
    make_arcane_turret,
    make_blink_fox,
    make_plague_rat,
    make_mind_flayer,
    make_curse_priest,
    make_rat_swarm,
]
