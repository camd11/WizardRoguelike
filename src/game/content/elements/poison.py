"""Poison element — heavy DOT, weak initial hit."""
from __future__ import annotations

from game.constants import Tags
from game.core.buff import Buff


class VenomBuff(Buff):
    """Deals poison damage each turn. Stacks with multiple applications."""

    def __init__(self, damage: int = 4) -> None:
        self._venom_damage = damage
        super().__init__()

    def on_init(self) -> None:
        self.name = "Envenomed"
        self.color = (100, 200, 0)
        self.description = f"Takes {self._venom_damage} poison damage per turn."

    def on_advance(self) -> None:
        if self.owner and self.owner.level:
            self.owner.level.deal_damage(
                self.owner.x, self.owner.y,
                self._venom_damage, Tags.Poison, self,
            )


def apply_secondary(spell, level, x: int, y: int) -> None:
    """Apply heavy poison DOT to the target."""
    unit = level.get_unit_at(x, y)
    if unit and unit.is_alive() and unit.team != spell.caster.team:
        dot_damage = getattr(spell, '_element_dot_damage', 4)
        dot_duration = getattr(spell, '_element_dot_duration', 5)
        if dot_duration > 0:
            venom = VenomBuff(damage=dot_damage)
            unit.apply_buff(venom, duration=dot_duration)
