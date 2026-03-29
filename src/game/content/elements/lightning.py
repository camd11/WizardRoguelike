"""Lightning element — shock/stun secondary effect."""
from __future__ import annotations

from game.constants import StackType
from game.core.buff import Buff


class StunBuff(Buff):
    """Stunned — skip next turn."""

    def on_init(self) -> None:
        self.name = "Stunned"
        self.color = (255, 255, 60)
        self.stack_type = StackType.STACK_DURATION
        self.description = "Stunned. Cannot act."


def apply_secondary(spell, level, x: int, y: int) -> None:
    """25% chance to stun the target for 1 turn."""
    unit = level.get_unit_at(x, y)
    if unit and unit.is_alive() and unit.team != spell.caster.team:
        # Deterministic stun chance based on position + turn
        turn = level.turn_no if level else 0
        stun_roll = hash((x, y, turn, "lightning_stun")) % 100
        if stun_roll < 25:
            stun = StunBuff()
            unit.apply_buff(stun, duration=1)
