"""Buff/debuff system with stack types, stat bonuses, and event triggers.

Replicates RW2's symmetric apply/unapply pattern (Level.py:956-1077):
stat bonuses are accumulated on apply() and reversed on unapply().
"""
from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any, Callable

from game.constants import BuffType, StackType, Tag

if TYPE_CHECKING:
    from game.core.events import EventHandler
    from game.core.unit import Unit


class Buff:
    """A temporary or permanent effect applied to a unit.

    Lifecycle:
        1. on_init() — set name, triggers, resists, bonuses
        2. apply(owner) — accumulate stats onto owner, subscribe events
        3. advance() — tick per turn, call on_advance(), auto-remove at 0
        4. unapply() — reverse accumulation, unsubscribe
    """

    def __init__(self) -> None:
        self.name: str = "Buff"
        self.description: str = ""
        self.turns_left: int = 0  # 0 = permanent
        self.color: tuple[int, int, int] = (255, 255, 255)
        self.buff_type: BuffType = BuffType.BUFF
        self.stack_type: StackType = StackType.STACK_DURATION

        # Owner reference (set during apply)
        self.owner: Unit | None = None

        # Event triggers: {event_type: callback}
        self.owner_triggers: dict[type, Callable] = {}
        self.global_triggers: dict[type, Callable] = {}

        # Stat bonuses (applied to owner on apply, removed on unapply)
        self.resists: dict[Tag, int] = {}
        self.global_bonuses: dict[str, int] = defaultdict(int)
        self.global_bonuses_pct: dict[str, int] = defaultdict(int)
        self.tag_bonuses: dict[Tag, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.tag_bonuses_pct: dict[Tag, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        # Tags this buff is associated with
        self.tags: list[Tag] = []

        self.on_init()

    def on_init(self) -> None:
        """Override to configure the buff. Called from __init__."""
        pass

    def apply(self, owner: Unit) -> bool:
        """Attach this buff to a unit. Returns False if rejected by stack rules."""
        self.owner = owner

        # Check existing buffs of same type for stack behavior
        existing = owner.get_buff(type(self))
        if existing is not None:
            if self.stack_type == StackType.STACK_NONE:
                return False
            elif self.stack_type == StackType.STACK_DURATION:
                existing.turns_left = max(existing.turns_left, self.turns_left)
                return False
            elif self.stack_type == StackType.STACK_REPLACE:
                owner.remove_buff(existing)
            elif self.stack_type == StackType.STACK_INTENSITY:
                pass  # Allow multiple instances

        owner.buffs.append(self)

        # Accumulate stat bonuses onto owner
        self._accumulate_bonuses(owner, 1)

        # Subscribe event triggers
        if owner.level is not None:
            self._subscribe_events(owner.level.event_handler)

        self.on_applied(owner)
        return True

    def unapply(self) -> None:
        """Remove this buff from its owner. Reverses stat accumulation."""
        if self.owner is None:
            return

        owner = self.owner

        # Unsubscribe event triggers
        if owner.level is not None:
            self._unsubscribe_events(owner.level.event_handler)

        # Reverse stat bonuses
        self._accumulate_bonuses(owner, -1)

        self.on_unapplied()
        self.owner = None

    def advance(self) -> None:
        """Called once per turn. Ticks duration and calls on_advance()."""
        self.on_advance()
        if self.turns_left > 0:
            self.turns_left -= 1
            if self.turns_left == 0:
                if self.owner is not None:
                    self.owner.remove_buff(self)

    def _accumulate_bonuses(self, owner: Unit, sign: int) -> None:
        """Add (sign=1) or remove (sign=-1) stat bonuses from owner."""
        for tag, amount in self.resists.items():
            owner.resists[tag] = owner.resists.get(tag, 0) + sign * amount

        for attr, amount in self.global_bonuses.items():
            owner.global_bonuses[attr] += sign * amount

        for attr, amount in self.global_bonuses_pct.items():
            owner.global_bonuses_pct[attr] += sign * amount

        for tag, bonuses in self.tag_bonuses.items():
            for attr, amount in bonuses.items():
                owner.tag_bonuses[tag][attr] += sign * amount

        for tag, bonuses in self.tag_bonuses_pct.items():
            for attr, amount in bonuses.items():
                owner.tag_bonuses_pct[tag][attr] += sign * amount

    def _subscribe_events(self, handler: EventHandler) -> None:
        for event_type, callback in self.owner_triggers.items():
            handler.subscribe(event_type, callback, entity=self.owner)
        for event_type, callback in self.global_triggers.items():
            handler.subscribe(event_type, callback, entity=None)

    def _unsubscribe_events(self, handler: EventHandler) -> None:
        for event_type, callback in self.owner_triggers.items():
            handler.unsubscribe(event_type, callback, entity=self.owner)
        for event_type, callback in self.global_triggers.items():
            handler.unsubscribe(event_type, callback, entity=None)

    # Override hooks
    def on_applied(self, owner: Unit) -> None:
        """Called after buff is successfully applied."""
        pass

    def on_unapplied(self) -> None:
        """Called before buff is removed."""
        pass

    def on_advance(self) -> None:
        """Called each turn while buff is active."""
        pass

    def __repr__(self) -> str:
        dur = f" ({self.turns_left}t)" if self.turns_left > 0 else ""
        return f"{self.name}{dur}"
