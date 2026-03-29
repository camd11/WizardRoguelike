"""Spell synergy system — combo bonuses when owning specific element pairs.

Synergies are passive bonuses that activate when the player owns two
complementary elements. This rewards diverse builds over single-element focus.

Synergies are checked after each component purchase and applied as permanent buffs.
"""
from __future__ import annotations

from dataclasses import dataclass

from game.constants import Tag, Tags
from game.core.buff import Buff


@dataclass(frozen=True)
class Synergy:
    """A synergy bonus activated by owning two specific elements."""
    name: str
    element_a: str
    element_b: str
    description: str
    bonuses: dict[str, int]  # global bonuses
    tag_bonuses: dict[str, dict[str, int]]  # {tag_name: {attr: amount}}


class SynergyBuff(Buff):
    """Permanent buff applied when a synergy is activated."""

    def __init__(self, synergy: Synergy) -> None:
        self._synergy = synergy
        super().__init__()

    def on_init(self) -> None:
        self.name = self._synergy.name
        self.description = self._synergy.description
        self.color = (200, 180, 255)

        for attr, amount in self._synergy.bonuses.items():
            self.global_bonuses[attr] = amount

        for tag_name, attrs in self._synergy.tag_bonuses.items():
            tag = Tag.get(tag_name)
            for attr, amount in attrs.items():
                self.tag_bonuses[tag][attr] = amount


# Define all synergies
ALL_SYNERGIES = [
    Synergy(
        name="Steam Power",
        element_a="Fire", element_b="Ice",
        description="Fire + Ice: +2 damage to all spells",
        bonuses={"damage": 2},
        tag_bonuses={},
    ),
    Synergy(
        name="Tempest",
        element_a="Lightning", element_b="Dark",
        description="Lightning + Dark: +15% damage to Lightning and Dark spells",
        bonuses={},
        tag_bonuses={"Lightning": {"damage": 2}, "Dark": {"damage": 2}},
    ),
    Synergy(
        name="Blight",
        element_a="Nature", element_b="Poison",
        description="Nature + Poison: +3 DOT damage, +1 DOT duration",
        bonuses={},
        tag_bonuses={"Nature": {"damage": 2}, "Poison": {"damage": 2}},
    ),
    Synergy(
        name="Divine Wrath",
        element_a="Holy", element_b="Lightning",
        description="Holy + Lightning: +3 damage to Holy and Lightning spells",
        bonuses={},
        tag_bonuses={"Holy": {"damage": 3}, "Lightning": {"damage": 1}},
    ),
    Synergy(
        name="Void Weave",
        element_a="Arcane", element_b="Dark",
        description="Arcane + Dark: +2 range to all spells",
        bonuses={"range": 2},
        tag_bonuses={},
    ),
    Synergy(
        name="Elemental Trinity",
        element_a="Fire", element_b="Lightning",
        description="Fire + Lightning: +1 radius to Burst and Cone spells",
        bonuses={},
        tag_bonuses={"Shape_Burst": {"radius": 1}, "Shape_Cone": {"radius": 1}},
    ),
    Synergy(
        name="Frostbite",
        element_a="Ice", element_b="Poison",
        description="Ice + Poison: enemies frozen by Ice take +50% Poison damage",
        bonuses={},
        tag_bonuses={"Poison": {"damage": 3}},
    ),
]


class SynergyTracker:
    """Tracks active synergies and applies/removes buffs."""

    def __init__(self) -> None:
        self.active: set[str] = set()  # Names of active synergies

    def check_synergies(self, owned_elements: set[str], player_unit) -> list[str]:
        """Check for new synergies and apply buffs. Returns list of newly activated names."""
        newly_activated = []

        for synergy in ALL_SYNERGIES:
            if synergy.name in self.active:
                continue
            if synergy.element_a in owned_elements and synergy.element_b in owned_elements:
                buff = SynergyBuff(synergy)
                player_unit.apply_buff(buff)
                self.active.add(synergy.name)
                newly_activated.append(synergy.name)

        return newly_activated

    def get_active_synergies(self) -> list[Synergy]:
        """Get list of active synergy objects."""
        return [s for s in ALL_SYNERGIES if s.name in self.active]
