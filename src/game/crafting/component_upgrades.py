"""Component mastery system — buy upgrades that enhance all spells using a component.

Element Mastery: Fire Mastery I (+2 damage to all Fire spells), II (+4), III (+6)
Shape Mastery: Bolt Mastery (+1 range), Burst Mastery (+1 radius), etc.
Modifier Mastery: Empowered Mastery (damage mult 1.5 → 1.75), etc.

Masteries are implemented as permanent buffs with tag_bonuses, applied to the
player unit. They use the existing stat pipeline — no engine changes needed.
"""
from __future__ import annotations

from dataclasses import dataclass

from game.constants import Tag, Tags
from game.core.buff import Buff


@dataclass
class MasteryLevel:
    """A single mastery upgrade."""
    name: str
    tag: Tag
    level: int  # 1, 2, or 3
    sp_cost: int
    bonuses: dict[str, int]  # {"damage": 2, "range": 1, ...}
    bonuses_pct: dict[str, int]  # {"damage": 10, ...}


class MasteryBuff(Buff):
    """Permanent buff that applies tag-based stat bonuses."""

    def __init__(self, mastery: MasteryLevel) -> None:
        self._mastery = mastery
        super().__init__()

    def on_init(self) -> None:
        self.name = self._mastery.name
        self.description = f"Level {self._mastery.level} mastery"
        self.color = self._mastery.tag.color

        # Apply bonuses as tag_bonuses
        for attr, amount in self._mastery.bonuses.items():
            self.tag_bonuses[self._mastery.tag][attr] = amount
        for attr, amount in self._mastery.bonuses_pct.items():
            self.tag_bonuses_pct[self._mastery.tag][attr] = amount


# ---------------------------------------------------------------------------
# Element mastery definitions
# ---------------------------------------------------------------------------
def _elem_masteries(name: str, tag: Tag) -> list[MasteryLevel]:
    return [
        MasteryLevel(f"{name} Mastery I", tag, 1, 2, {"damage": 2}, {}),
        MasteryLevel(f"{name} Mastery II", tag, 2, 3, {"damage": 4}, {}),
        MasteryLevel(f"{name} Mastery III", tag, 3, 5, {"damage": 6}, {"damage": 15}),
    ]


ELEMENT_MASTERIES: dict[str, list[MasteryLevel]] = {
    "Fire": _elem_masteries("Fire", Tags.Fire),
    "Ice": _elem_masteries("Ice", Tags.Ice),
    "Lightning": _elem_masteries("Lightning", Tags.Lightning),
    "Dark": _elem_masteries("Dark", Tags.Dark),
    "Holy": _elem_masteries("Holy", Tags.Holy),
    "Nature": _elem_masteries("Nature", Tags.Nature),
    "Arcane": _elem_masteries("Arcane", Tags.Arcane),
    "Poison": _elem_masteries("Poison", Tags.Poison),
}

# ---------------------------------------------------------------------------
# Shape mastery definitions
# ---------------------------------------------------------------------------
SHAPE_MASTERIES: dict[str, list[MasteryLevel]] = {
    "Bolt": [
        MasteryLevel("Bolt Mastery I", Tags.Shape_Bolt, 1, 2, {"range": 1}, {}),
        MasteryLevel("Bolt Mastery II", Tags.Shape_Bolt, 2, 3, {"range": 2}, {}),
    ],
    "Burst": [
        MasteryLevel("Burst Mastery I", Tags.Shape_Burst, 1, 2, {"radius": 1}, {}),
        MasteryLevel("Burst Mastery II", Tags.Shape_Burst, 2, 4, {"radius": 1, "damage": 2}, {}),
    ],
    "Beam": [
        MasteryLevel("Beam Mastery I", Tags.Shape_Beam, 1, 2, {"range": 2}, {}),
        MasteryLevel("Beam Mastery II", Tags.Shape_Beam, 2, 3, {"damage": 3}, {}),
    ],
    "Cone": [
        MasteryLevel("Cone Mastery I", Tags.Shape_Cone, 1, 2, {"radius": 1}, {}),
        MasteryLevel("Cone Mastery II", Tags.Shape_Cone, 2, 4, {"damage": 3, "radius": 1}, {}),
    ],
    "Touch": [
        MasteryLevel("Touch Mastery I", Tags.Shape_Touch, 1, 2, {"damage": 3}, {}),
        MasteryLevel("Touch Mastery II", Tags.Shape_Touch, 2, 3, {"damage": 5}, {}),
    ],
    "Orb": [
        MasteryLevel("Orb Mastery I", Tags.Shape_Orb, 1, 2, {"damage": 2}, {}),
    ],
    "Self": [
        MasteryLevel("Aura Mastery I", Tags.Shape_Self, 1, 2, {"damage": 2, "duration": 2}, {}),
    ],
    "Summon": [
        MasteryLevel("Summon Mastery I", Tags.Shape_Summon, 1, 2, {"damage": 3}, {}),
    ],
}


class MasteryTracker:
    """Tracks which masteries the player has purchased."""

    def __init__(self) -> None:
        self.purchased: dict[str, int] = {}  # "Fire": 2 means Fire Mastery II

    def get_available(self, owned_elements: set[str], owned_shapes: set[str]) -> list[MasteryLevel]:
        """Get all masteries available for purchase."""
        available = []

        for elem_name in owned_elements:
            masteries = ELEMENT_MASTERIES.get(elem_name, [])
            current = self.purchased.get(elem_name, 0)
            if current < len(masteries):
                available.append(masteries[current])

        for shape_name in owned_shapes:
            masteries = SHAPE_MASTERIES.get(shape_name, [])
            key = f"Shape_{shape_name}"
            current = self.purchased.get(key, 0)
            if current < len(masteries):
                available.append(masteries[current])

        return available

    def buy(self, mastery: MasteryLevel, player_unit) -> bool:
        """Purchase a mastery and apply the buff."""
        # Determine tracking key
        for elem_name, masteries in ELEMENT_MASTERIES.items():
            if mastery in masteries:
                key = elem_name
                break
        else:
            for shape_name, masteries in SHAPE_MASTERIES.items():
                if mastery in masteries:
                    key = f"Shape_{shape_name}"
                    break
            else:
                return False

        # Remove previous mastery buff if upgrading
        current = self.purchased.get(key, 0)
        if current > 0:
            # Find and remove old mastery buff
            for buff in list(player_unit.buffs):
                if isinstance(buff, MasteryBuff) and buff._mastery.tag == mastery.tag:
                    if buff._mastery.level < mastery.level:
                        player_unit.remove_buff(buff)

        # Apply new mastery
        buff = MasteryBuff(mastery)
        player_unit.apply_buff(buff)
        self.purchased[key] = mastery.level
        return True
