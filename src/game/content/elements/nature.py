"""Nature element — poison DOT secondary effect."""
from __future__ import annotations

from game.constants import Tags
from game.core.buff import Buff


class PoisonBuff(Buff):
    """Deals nature/poison damage each turn."""

    def __init__(self, damage: int = 3) -> None:
        self._poison_damage = damage
        super().__init__()

    def on_init(self) -> None:
        self.name = "Poisoned"
        self.color = (50, 200, 50)
        self.description = f"Takes {self._poison_damage} nature damage per turn."

    def on_advance(self) -> None:
        if self.owner and self.owner.level:
            self.owner.level.deal_damage(
                self.owner.x, self.owner.y,
                self._poison_damage, Tags.Nature, self,
            )


def apply_secondary(spell, level, x: int, y: int) -> None:
    """Apply poison DOT to the target."""
    unit = level.get_unit_at(x, y)
    if unit and unit.is_alive() and unit.team != spell.caster.team:
        dot_damage = getattr(spell, '_element_dot_damage', 3)
        dot_duration = getattr(spell, '_element_dot_duration', 4)
        if dot_duration > 0:
            poison = PoisonBuff(damage=dot_damage)
            unit.apply_buff(poison, duration=dot_duration)
