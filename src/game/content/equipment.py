"""Equipment items — permanent buffs that occupy an equipment slot.

Each equipment piece is a Buff subclass with a slot (EquipSlot), tier (1-3),
and stat bonuses configured in on_init(). The Unit class applies them via
its existing buff system; no Unit modifications needed.

Modeled on Rift Wizard 2's equipment-as-buff pattern.
"""
from __future__ import annotations

import random
from typing import TYPE_CHECKING

from game.constants import BuffType, EquipSlot, StackType, Tags
from game.core.buff import Buff
from game.core.events import EventOnDeath

if TYPE_CHECKING:
    from game.core.unit import Unit


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------
class Equipment(Buff):
    """Base class for all equipment items."""

    slot: EquipSlot = EquipSlot.STAFF  # Override in subclass
    tier: int = 1  # 1-3, used for shop pricing and drop tables

    def on_init(self) -> None:
        self.buff_type = BuffType.EQUIPMENT
        self.stack_type = StackType.STACK_REPLACE
        self.turns_left = 0  # permanent


# ===========================================================================
# STAFFS — affect spell damage
# ===========================================================================

class ApprenticeStaff(Equipment):
    slot = EquipSlot.STAFF
    tier = 1

    def on_init(self) -> None:
        super().on_init()
        self.name = "Apprentice Staff"
        self.description = "+2 damage to all spells."
        self.color = (180, 140, 80)
        self.global_bonuses["damage"] = 2


class FireStaff(Equipment):
    slot = EquipSlot.STAFF
    tier = 2

    def on_init(self) -> None:
        super().on_init()
        self.name = "Fire Staff"
        self.description = "+3 damage to Fire spells."
        self.color = (255, 80, 20)
        self.tag_bonuses[Tags.Fire]["damage"] = 3


class IceStaff(Equipment):
    slot = EquipSlot.STAFF
    tier = 2

    def on_init(self) -> None:
        super().on_init()
        self.name = "Ice Staff"
        self.description = "+3 damage to Ice spells."
        self.color = (100, 200, 255)
        self.tag_bonuses[Tags.Ice]["damage"] = 3


class ArcaneStaff(Equipment):
    slot = EquipSlot.STAFF
    tier = 3

    def on_init(self) -> None:
        super().on_init()
        self.name = "Arcane Staff"
        self.description = "+5 damage to Arcane spells, -1 range to all spells."
        self.color = (180, 80, 255)
        self.tag_bonuses[Tags.Arcane]["damage"] = 5
        self.global_bonuses["range"] = -1


class StaffOfPower(Equipment):
    slot = EquipSlot.STAFF
    tier = 3

    def on_init(self) -> None:
        super().on_init()
        self.name = "Staff of Power"
        self.description = "+4 damage, +1 range to all spells."
        self.color = (220, 200, 255)
        self.global_bonuses["damage"] = 4
        self.global_bonuses["range"] = 1


# ===========================================================================
# ROBES — defense / HP
# ===========================================================================

class ClothRobe(Equipment):
    slot = EquipSlot.ROBE
    tier = 1

    def on_init(self) -> None:
        super().on_init()
        self.name = "Cloth Robe"
        self.description = "+10 max HP."
        self.color = (160, 140, 120)

    def on_applied(self, owner: Unit) -> None:
        owner.max_hp += 10
        owner.cur_hp += 10

    def on_unapplied(self) -> None:
        if self.owner:
            self.owner.max_hp -= 10
            self.owner.cur_hp = min(self.owner.cur_hp, self.owner.max_hp)


class FireRobe(Equipment):
    slot = EquipSlot.ROBE
    tier = 2

    def on_init(self) -> None:
        super().on_init()
        self.name = "Fire Robe"
        self.description = "+50 Fire resist."
        self.color = (255, 100, 40)
        self.resists[Tags.Fire] = 50


class IceRobe(Equipment):
    slot = EquipSlot.ROBE
    tier = 2

    def on_init(self) -> None:
        super().on_init()
        self.name = "Ice Robe"
        self.description = "+50 Ice resist."
        self.color = (80, 180, 240)
        self.resists[Tags.Ice] = 50


class RobeOfVitality(Equipment):
    slot = EquipSlot.ROBE
    tier = 3

    def on_init(self) -> None:
        super().on_init()
        self.name = "Robe of Vitality"
        self.description = "+20 max HP, +1 HP regen per turn."
        self.color = (50, 200, 50)

    def on_applied(self, owner: Unit) -> None:
        owner.max_hp += 20
        owner.cur_hp += 20

    def on_unapplied(self) -> None:
        if self.owner:
            self.owner.max_hp -= 20
            self.owner.cur_hp = min(self.owner.cur_hp, self.owner.max_hp)

    def on_advance(self) -> None:
        if self.owner:
            heal = min(1, self.owner.max_hp - self.owner.cur_hp)
            if heal > 0:
                self.owner.cur_hp += heal


# ===========================================================================
# HEAD — utility
# ===========================================================================

class WizardHat(Equipment):
    slot = EquipSlot.HEAD
    tier = 1

    def on_init(self) -> None:
        super().on_init()
        self.name = "Wizard Hat"
        self.description = "+1 range to all spells."
        self.color = (100, 80, 180)
        self.global_bonuses["range"] = 1


class CrownOfClarity(Equipment):
    slot = EquipSlot.HEAD
    tier = 2

    def on_init(self) -> None:
        super().on_init()
        self.name = "Crown of Clarity"
        self.description = "+1 charge to all spells."
        self.color = (255, 255, 200)
        self.global_bonuses["max_charges"] = 1


class SeersCirclet(Equipment):
    slot = EquipSlot.HEAD
    tier = 3

    def on_init(self) -> None:
        super().on_init()
        self.name = "Seer's Circlet"
        self.description = "+2 range to all spells."
        self.color = (200, 180, 255)
        self.global_bonuses["range"] = 2


# ===========================================================================
# GLOVES — casting
# ===========================================================================

class GlovesOfPower(Equipment):
    slot = EquipSlot.GLOVES
    tier = 1

    def on_init(self) -> None:
        super().on_init()
        self.name = "Gloves of Power"
        self.description = "+1 damage to all spells."
        self.color = (200, 160, 120)
        self.global_bonuses["damage"] = 1


class GlovesOfHaste(Equipment):
    slot = EquipSlot.GLOVES
    tier = 2

    def on_init(self) -> None:
        super().on_init()
        self.name = "Gloves of Haste"
        self.description = "Spell cooldowns reduced by 1."
        self.color = (255, 200, 100)
        self.global_bonuses["cooldown"] = -1


class LightningGloves(Equipment):
    slot = EquipSlot.GLOVES
    tier = 2

    def on_init(self) -> None:
        super().on_init()
        self.name = "Lightning Gloves"
        self.description = "+3 damage to Lightning spells."
        self.color = (255, 255, 60)
        self.tag_bonuses[Tags.Lightning]["damage"] = 3


# ===========================================================================
# BOOTS — movement
# ===========================================================================

class LeatherBoots(Equipment):
    slot = EquipSlot.BOOTS
    tier = 1

    def on_init(self) -> None:
        super().on_init()
        self.name = "Leather Boots"
        self.description = "Sturdy leather boots."
        self.color = (140, 100, 60)


class BootsOfSpeed(Equipment):
    slot = EquipSlot.BOOTS
    tier = 2

    def on_init(self) -> None:
        super().on_init()
        self.name = "Boots of Speed"
        self.description = "Move swiftly."
        self.color = (200, 200, 100)


class FlyingBoots(Equipment):
    slot = EquipSlot.BOOTS
    tier = 3

    def on_init(self) -> None:
        super().on_init()
        self.name = "Flying Boots"
        self.description = "Grants flying."
        self.color = (200, 220, 255)

    def on_applied(self, owner: Unit) -> None:
        owner.flying = True

    def on_unapplied(self) -> None:
        if self.owner:
            self.owner.flying = False


# ===========================================================================
# AMULETS — special passives
# ===========================================================================

class AmuletOfShields(Equipment):
    slot = EquipSlot.AMULET
    tier = 2

    def on_init(self) -> None:
        super().on_init()
        self.name = "Amulet of Shields"
        self.description = "Start each level with 2 shields."
        self.color = (200, 200, 255)
        # The shield grant happens on apply (entering a new level re-equips).
        # For mid-level equip, grant immediately as well.

    def on_applied(self, owner: Unit) -> None:
        owner.shields += 2

    def on_unapplied(self) -> None:
        if self.owner:
            self.owner.shields = max(0, self.owner.shields - 2)


class AmuletOfLife(Equipment):
    slot = EquipSlot.AMULET
    tier = 1

    def on_init(self) -> None:
        super().on_init()
        self.name = "Amulet of Life"
        self.description = "+5 max HP, +25 Holy resist."
        self.color = (255, 255, 200)
        self.resists[Tags.Holy] = 25

    def on_applied(self, owner: Unit) -> None:
        owner.max_hp += 5
        owner.cur_hp += 5

    def on_unapplied(self) -> None:
        if self.owner:
            self.owner.max_hp -= 5
            self.owner.cur_hp = min(self.owner.cur_hp, self.owner.max_hp)


# ===========================================================================
# Equipment pool and drop helper
# ===========================================================================

EQUIPMENT_POOL: dict[int, list[type[Equipment]]] = {
    1: [
        ApprenticeStaff,
        ClothRobe,
        WizardHat,
        GlovesOfPower,
        LeatherBoots,
        AmuletOfLife,
    ],
    2: [
        FireStaff,
        IceStaff,
        FireRobe,
        IceRobe,
        CrownOfClarity,
        GlovesOfHaste,
        LightningGloves,
        BootsOfSpeed,
        AmuletOfShields,
    ],
    3: [
        ArcaneStaff,
        StaffOfPower,
        RobeOfVitality,
        SeersCirclet,
        FlyingBoots,
    ],
}

# Flat list for convenience
ALL_EQUIPMENT: list[type[Equipment]] = [
    cls for tier_list in EQUIPMENT_POOL.values() for cls in tier_list
]


def get_equipment_drop(difficulty: int, rng: random.Random | None = None) -> Equipment:
    """Return a random equipment item appropriate for the given difficulty.

    Difficulty 1-5 maps to tier weights:
      - difficulty 1-2: mostly tier 1, some tier 2
      - difficulty 3:   mix of tier 1-2, rare tier 3
      - difficulty 4:   mostly tier 2, some tier 3
      - difficulty 5:   mostly tier 2-3

    Args:
        difficulty: Level difficulty (1-5).
        rng: Random instance for deterministic drops. Uses module random if None.
    """
    if rng is None:
        rng = random.Random()

    # Tier weights indexed by difficulty (1-based, index 0 unused)
    tier_weights: dict[int, dict[int, int]] = {
        1: {1: 90, 2: 10, 3: 0},
        2: {1: 60, 2: 35, 3: 5},
        3: {1: 30, 2: 50, 3: 20},
        4: {1: 10, 2: 50, 3: 40},
        5: {1: 0, 2: 35, 3: 65},
    }

    difficulty = max(1, min(5, difficulty))
    weights = tier_weights[difficulty]

    # Build weighted candidate list
    candidates: list[type[Equipment]] = []
    candidate_weights: list[int] = []

    for tier, pool in EQUIPMENT_POOL.items():
        w = weights.get(tier, 0)
        if w > 0:
            for cls in pool:
                candidates.append(cls)
                candidate_weights.append(w)

    chosen_cls = rng.choices(candidates, weights=candidate_weights, k=1)[0]
    return chosen_cls()
