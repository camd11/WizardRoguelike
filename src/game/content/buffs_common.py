"""Common buff/debuff definitions used by monsters and spells."""
from __future__ import annotations

from game.constants import StackType, Tags
from game.core.buff import Buff


class StunBuff(Buff):
    """Stunned — cannot act for duration."""
    def on_init(self) -> None:
        self.name = "Stunned"
        self.color = (255, 255, 60)
        self.stack_type = StackType.STACK_DURATION
        self.description = "Cannot act."


class BurnBuff(Buff):
    """Takes fire damage each turn."""
    def __init__(self, damage: int = 2) -> None:
        self._burn_dmg = damage
        super().__init__()

    def on_init(self) -> None:
        self.name = "Burning"
        self.color = (255, 80, 20)
        self.stack_type = StackType.STACK_DURATION
        self.description = f"Takes {self._burn_dmg} fire damage per turn."

    def on_advance(self) -> None:
        if self.owner and self.owner.level:
            self.owner.level.deal_damage(
                self.owner.x, self.owner.y, self._burn_dmg, Tags.Fire, self
            )


class FreezeBuff(Buff):
    """Frozen — cannot act, takes bonus ice damage."""
    def on_init(self) -> None:
        self.name = "Frozen"
        self.color = (100, 200, 255)
        self.stack_type = StackType.STACK_DURATION
        self.description = "Frozen solid. Cannot act."


class PoisonBuff(Buff):
    """Takes poison damage each turn."""
    def __init__(self, damage: int = 3) -> None:
        self._poison_dmg = damage
        super().__init__()

    def on_init(self) -> None:
        self.name = "Poisoned"
        self.color = (100, 200, 0)
        self.stack_type = StackType.STACK_DURATION
        self.description = f"Takes {self._poison_dmg} poison damage per turn."

    def on_advance(self) -> None:
        if self.owner and self.owner.level:
            self.owner.level.deal_damage(
                self.owner.x, self.owner.y, self._poison_dmg, Tags.Poison, self
            )


class BlindBuff(Buff):
    """Blinded — reduced range on all spells."""
    def on_init(self) -> None:
        self.name = "Blinded"
        self.color = (80, 80, 80)
        self.stack_type = StackType.STACK_DURATION
        self.global_bonuses["range"] = -3
        self.description = "Blinded. Spell range reduced by 3."


class ShieldBuff(Buff):
    """Grants temporary shields."""
    def __init__(self, shields: int = 1) -> None:
        self._shield_count = shields
        super().__init__()

    def on_init(self) -> None:
        self.name = "Shielded"
        self.color = (200, 200, 255)
        self.stack_type = StackType.STACK_REPLACE
        self.description = f"Absorbs {self._shield_count} hit(s)."

    def on_applied(self, owner) -> None:
        owner.shields += self._shield_count

    def on_unapplied(self) -> None:
        if self.owner:
            self.owner.shields = max(0, self.owner.shields - self._shield_count)


class RegenerationBuff(Buff):
    """Heals each turn."""
    def __init__(self, heal: int = 2) -> None:
        self._heal = heal
        super().__init__()

    def on_init(self) -> None:
        self.name = "Regenerating"
        self.color = (50, 255, 50)
        self.stack_type = StackType.STACK_DURATION
        self.description = f"Heals {self._heal} HP per turn."

    def on_advance(self) -> None:
        if self.owner:
            heal = min(self._heal, self.owner.max_hp - self.owner.cur_hp)
            if heal > 0:
                self.owner.cur_hp += heal


class HasteBufff(Buff):
    """Placeholder for haste — acts twice per turn. Future implementation."""
    def on_init(self) -> None:
        self.name = "Hasted"
        self.color = (255, 200, 100)
        self.stack_type = StackType.STACK_DURATION
        self.description = "Moves faster."
