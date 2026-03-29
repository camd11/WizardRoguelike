"""Fire element — burn DOT secondary effect."""
from __future__ import annotations

from typing import TYPE_CHECKING

from game.constants import Tags
from game.core.buff import Buff

if TYPE_CHECKING:
    from game.core.level import Level
    from game.core.spell_base import Spell
    from game.core.types import Point


class BurnBuff(Buff):
    """Deals fire damage each turn."""

    def __init__(self, damage: int = 2) -> None:
        self._burn_damage = damage
        super().__init__()

    def on_init(self) -> None:
        self.name = "Burn"
        self.color = (255, 80, 20)
        self.description = f"Takes {self._burn_damage} fire damage per turn."


    def on_advance(self) -> None:
        if self.owner and self.owner.level:
            self.owner.level.deal_damage(
                self.owner.x, self.owner.y,
                self._burn_damage, Tags.Fire, self,
            )


def apply_secondary(spell: Spell, level: Level, x: int, y: int) -> None:
    """Apply burn DOT to the target."""
    unit = level.get_unit_at(x, y)
    if unit and unit.is_alive() and unit.team != spell.caster.team:
        dot_damage = getattr(spell, '_element_dot_damage', 2)
        dot_duration = getattr(spell, '_element_dot_duration', 3)
        if dot_duration > 0:
            burn = BurnBuff(damage=dot_damage)
            unit.apply_buff(burn, duration=dot_duration)
