"""Self shape — cast on yourself, applies a buff/aura."""
from __future__ import annotations

from typing import Generator

from game.constants import StackType
from game.core.buff import Buff
from game.core.types import Point


class ElementalAuraBuff(Buff):
    """An aura that applies the spell's element as a buff to the caster."""

    def __init__(self, element_name: str, damage: int, damage_type, duration: int) -> None:
        self._aura_damage = damage
        self._aura_damage_type = damage_type
        self._aura_element_name = element_name
        self._aura_duration = duration
        super().__init__()

    def on_init(self) -> None:
        self.name = f"{self._aura_element_name} Aura"
        self.stack_type = StackType.STACK_REPLACE
        self.description = (
            f"Surrounded by {self._aura_element_name.lower()} energy. "
            f"Deals {self._aura_damage} damage to adjacent enemies each turn."
        )

    def on_advance(self) -> None:
        if self.owner and self.owner.level:
            from game.core.types import Point
            origin = Point(self.owner.x, self.owner.y)
            for p in origin.adjacent():
                if self.owner.level.in_bounds(p.x, p.y):
                    unit = self.owner.level.get_unit_at(p.x, p.y)
                    if unit and unit.team != self.owner.team:
                        self.owner.level.deal_damage(
                            p.x, p.y, self._aura_damage,
                            self._aura_damage_type, self,
                        )


def cast(spell, x: int, y: int) -> Generator[None, None, None]:
    """Apply an elemental aura to the caster."""
    caster = spell.caster
    damage = max(2, spell.get_stat("damage") * 2 // 3)  # Aura does 2/3 damage
    duration = spell.get_stat("duration") if spell.duration > 0 else 5

    aura = ElementalAuraBuff(
        element_name=spell._element.name,
        damage=damage,
        damage_type=spell.damage_type,
        duration=duration,
    )
    caster.apply_buff(aura, duration=duration)
    yield


def get_impacted_tiles(spell, x: int, y: int) -> list[Point]:
    if spell.caster:
        origin = Point(spell.caster.x, spell.caster.y)
        return [origin] + origin.adjacent()
    return [Point(x, y)]
