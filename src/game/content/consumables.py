"""Consumable items — one-time-use potions, scrolls, and bombs.

Found in levels and used via hotkey. Each consumable applies an immediate
effect and is then removed from the player's inventory.
"""
from __future__ import annotations

import random
from typing import TYPE_CHECKING

from game.constants import Tags
from game.content.buffs_common import ShieldBuff
from game.core.buff import Buff
from game.constants import StackType
from game.core.types import Point

if TYPE_CHECKING:
    from game.core.level import Level
    from game.core.unit import Unit


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class Consumable:
    """Base class for all consumable items."""

    def __init__(self) -> None:
        self.name: str = "Consumable"
        self.description: str = ""
        self.requires_target: bool = False

    def use(self, unit: Unit, level: Level, x: int | None = None,
            y: int | None = None) -> bool:
        """Apply the consumable effect. Returns True if successfully used."""
        return False

    def __repr__(self) -> str:
        return f"<{self.name}>"


# ---------------------------------------------------------------------------
# Buffs used by consumables
# ---------------------------------------------------------------------------

class HasteBuff(Buff):
    """Grants +1 move per turn."""
    def on_init(self) -> None:
        self.name = "Hasted"
        self.color = (255, 200, 100)
        self.stack_type = StackType.STACK_DURATION
        self.description = "+1 move per turn."


# ---------------------------------------------------------------------------
# Consumable definitions
# ---------------------------------------------------------------------------

class HealingPotion(Consumable):
    """Restores 30 HP to the user."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Healing Potion"
        self.description = "Restores 30 HP."
        self.requires_target = False

    def use(self, unit: Unit, level: Level, x: int | None = None,
            y: int | None = None) -> bool:
        heal = min(30, unit.max_hp - unit.cur_hp)
        if heal <= 0:
            return False
        unit.cur_hp += heal
        return True


class ManaScroll(Consumable):
    """Restores 3 charges to all spells."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Mana Scroll"
        self.description = "Restores 3 charges to all spells."
        self.requires_target = False

    def use(self, unit: Unit, level: Level, x: int | None = None,
            y: int | None = None) -> bool:
        restored = False
        for spell in unit.spells:
            if spell.max_charges > 0 and spell.cur_charges < spell.max_charges:
                spell.cur_charges = min(
                    spell.max_charges, spell.cur_charges + 3
                )
                restored = True
        return restored


class TeleportScroll(Consumable):
    """Teleport to a random floor tile."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Teleport Scroll"
        self.description = "Teleport to a random floor tile."
        self.requires_target = False

    def use(self, unit: Unit, level: Level, x: int | None = None,
            y: int | None = None) -> bool:
        floor_tiles: list[Point] = []
        for tx in range(level.width):
            for ty in range(level.height):
                tile = level.tiles[tx][ty]
                if tile.is_floor and tile.unit is None:
                    floor_tiles.append(Point(tx, ty))

        if not floor_tiles:
            return False

        target = random.choice(floor_tiles)
        return level.teleport(unit, target.x, target.y)


class ShieldPotion(Consumable):
    """Grants 2 shields."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Shield Potion"
        self.description = "Grants 2 shields."
        self.requires_target = False

    def use(self, unit: Unit, level: Level, x: int | None = None,
            y: int | None = None) -> bool:
        buff = ShieldBuff(shields=2)
        unit.apply_buff(buff, duration=0)
        return True


class HastePotion(Consumable):
    """Grants +1 move per turn for 5 turns."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Haste Potion"
        self.description = "+1 move per turn for 5 turns."
        self.requires_target = False

    def use(self, unit: Unit, level: Level, x: int | None = None,
            y: int | None = None) -> bool:
        buff = HasteBuff()
        unit.apply_buff(buff, duration=5)
        return True


class FireBomb(Consumable):
    """Deals 15 fire damage in radius 2 at target location."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Fire Bomb"
        self.description = "Deals 15 fire damage in radius 2."
        self.requires_target = True

    def use(self, unit: Unit, level: Level, x: int | None = None,
            y: int | None = None) -> bool:
        if x is None or y is None:
            return False
        if not level.in_bounds(x, y):
            return False

        origin = Point(x, y)
        targets = level.get_units_in_ball(origin, radius=2)
        for target in targets:
            level.deal_damage(target.x, target.y, 15, Tags.Fire, self)
        return True


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ALL_CONSUMABLES: list[type[Consumable]] = [
    HealingPotion,
    ManaScroll,
    TeleportScroll,
    ShieldPotion,
    HastePotion,
    FireBomb,
]


def get_random_consumable(rng: random.Random) -> Consumable:
    """Return a random consumable instance."""
    cls = rng.choice(ALL_CONSUMABLES)
    return cls()


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

class ConsumableInventory:
    """Holds the player's consumable items. Maximum 6 slots."""

    MAX_SLOTS = 6

    def __init__(self) -> None:
        self._items: list[Consumable] = []

    def add(self, consumable: Consumable) -> bool:
        """Add a consumable. Returns False if inventory is full."""
        if len(self._items) >= self.MAX_SLOTS:
            return False
        self._items.append(consumable)
        return True

    def use(self, index: int, unit: Unit, level: Level,
            x: int | None = None, y: int | None = None) -> bool:
        """Use the consumable at the given index. Removes it on success."""
        if index < 0 or index >= len(self._items):
            return False
        consumable = self._items[index]
        if consumable.use(unit, level, x, y):
            self._items.pop(index)
            return True
        return False

    def get_items(self) -> list[Consumable]:
        """Return a copy of the current inventory list."""
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        return f"<ConsumableInventory ({len(self._items)}/{self.MAX_SLOTS})>"
