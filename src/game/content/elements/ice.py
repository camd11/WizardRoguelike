"""Ice element — freeze/slow secondary effect."""
from __future__ import annotations

from typing import TYPE_CHECKING

from game.constants import StackType
from game.core.buff import Buff

if TYPE_CHECKING:
    from game.core.level import Level
    from game.core.spell_base import Spell


class FreezeBuff(Buff):
    """Freezes target — they skip their next turn."""

    def on_init(self) -> None:
        self.name = "Frozen"
        self.color = (100, 200, 255)
        self.stack_type = StackType.STACK_DURATION
        self.description = "Frozen solid. Cannot act."
        self._frozen = False

    def on_applied(self, owner) -> None:
        self._frozen = True

    def on_advance(self) -> None:
        # Unit is immobilized while frozen (handled by turn system checking for freeze)
        pass


def apply_secondary(spell, level, x: int, y: int) -> None:
    """Apply freeze to the target."""
    unit = level.get_unit_at(x, y)
    if unit and unit.is_alive() and unit.team != spell.caster.team:
        freeze = FreezeBuff()
        unit.apply_buff(freeze, duration=1)
