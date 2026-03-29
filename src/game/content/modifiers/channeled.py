"""Channeled modifier — sustain the spell for multiple turns."""
from __future__ import annotations

from game.constants import StackType
from game.core.buff import Buff


class ChannelBuff(Buff):
    """Buff applied to caster while channeling. Re-casts the spell each turn."""

    def __init__(self, spell, target_x: int, target_y: int, turns: int) -> None:
        self._channel_spell = spell
        self._target_x = target_x
        self._target_y = target_y
        self._channel_turns = turns
        super().__init__()

    def on_init(self) -> None:
        self.name = "Channeling"
        self.color = (200, 200, 255)
        self.stack_type = StackType.STACK_REPLACE
        self.description = f"Channeling {self._channel_spell.name}."

    def on_advance(self) -> None:
        if self.owner and self.owner.level:
            # Re-cast the spell at the same target
            gen = self._channel_spell._shape_cast(self._target_x, self._target_y)
            self.owner.level.queue_spell(gen, self.owner)


def modify_stats(spell, stats: dict) -> dict:
    return stats


def apply_effect(spell, level, x: int, y: int) -> None:
    """Apply channel buff to caster (handled during CraftedSpell.cast)."""
    # Channeling is handled at the CraftedSpell.cast level, not post-hit
    pass
