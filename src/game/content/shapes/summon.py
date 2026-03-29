"""Summon shape — creates an elemental minion at target location."""
from __future__ import annotations

from typing import Generator

from game.constants import Tags, Team
from game.core.spell_base import Spell
from game.core.types import Point
from game.core.unit import Unit


def _create_elemental(element_name: str, damage: int, damage_type, hp: int) -> Unit:
    """Create a basic elemental minion."""
    unit = Unit()
    unit.name = f"{element_name} Elemental"
    unit.team = Team.PLAYER  # Summons are allies
    unit.max_hp = hp
    unit.cur_hp = hp
    unit.tags = [Tags.Construct]

    # Give the elemental a simple melee attack
    class ElementalAttack(Spell):
        def on_init(self_inner):
            self_inner.name = f"{element_name} Strike"
            self_inner.damage = damage
            self_inner.damage_type = damage_type
            self_inner.range = 1
            self_inner.melee = True
            self_inner.tags = []

        def cast(self_inner, x, y):
            if self_inner.level:
                self_inner.level.deal_damage(
                    x, y, self_inner.get_stat("damage"),
                    self_inner.damage_type, self_inner,
                )
            yield

    unit.add_spell(ElementalAttack())
    return unit


def cast(spell, x: int, y: int) -> Generator[None, None, None]:
    """Summon an elemental minion at the target location."""
    level = spell.level
    caster = spell.caster

    # Check tile is empty
    if level.get_unit_at(x, y) is not None:
        yield
        return

    damage = max(1, spell.get_stat("damage") // 2)
    hp = spell.get_stat("damage") * 3  # Summon HP scales with spell damage
    duration = spell.get_stat("duration") if spell.duration > 0 else 8

    elemental = _create_elemental(
        element_name=spell._element.name,
        damage=damage,
        damage_type=spell.damage_type,
        hp=hp,
    )
    elemental.turns_to_death = duration

    level.add_unit(elemental, x, y)
    yield


def get_impacted_tiles(spell, x: int, y: int) -> list[Point]:
    return [Point(x, y)]
