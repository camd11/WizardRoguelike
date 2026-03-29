"""Event system for combat, buffs, and game state changes.

Replicates RW2's EventHandler pattern (Level.py:150-185) with
snapshot-before-iteration to prevent handler mutation during dispatch.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, NamedTuple


# ---------------------------------------------------------------------------
# Event types (immutable records)
# ---------------------------------------------------------------------------
class EventOnSpellCast(NamedTuple):
    spell: Any       # Spell instance
    caster: Any      # Unit
    x: int
    y: int
    pay_costs: bool


class EventOnPreDamaged(NamedTuple):
    unit: Any           # Unit about to take damage
    damage: int         # Damage after resistance
    original_damage: int  # Damage before resistance
    damage_type: Any    # Tag
    source: Any         # Spell/Buff


class EventOnDamaged(NamedTuple):
    unit: Any
    damage: int
    damage_type: Any
    source: Any


class EventOnHealed(NamedTuple):
    unit: Any
    heal: int
    source: Any


class EventOnDeath(NamedTuple):
    unit: Any
    damage_event: Any  # DamageEvent or None


class EventOnBuffApply(NamedTuple):
    buff: Any
    unit: Any


class EventOnBuffRemove(NamedTuple):
    buff: Any
    unit: Any


class EventOnMoved(NamedTuple):
    unit: Any
    x: int
    y: int
    teleport: bool


class EventOnUnitAdded(NamedTuple):
    unit: Any


class EventOnPass(NamedTuple):
    unit: Any


class EventOnTurnEnd(NamedTuple):
    turn_no: int


# ---------------------------------------------------------------------------
# EventHandler — entity + global triggers, snapshot-safe dispatch
# ---------------------------------------------------------------------------
class EventHandler:
    """Central event dispatcher.

    Supports both entity-specific triggers (fire only when event targets
    a specific unit) and global triggers (fire for all events of that type).

    Handlers are snapshot-listed before iteration to prevent mutation during
    dispatch (matching RW2 Level.py:178-180).
    """

    def __init__(self) -> None:
        # {event_type: {entity_or_None: [callbacks]}}
        self._triggers: dict[type, dict[Any, list[Callable]]] = defaultdict(
            lambda: defaultdict(list)
        )

    def subscribe(self, event_type: type, callback: Callable, entity: Any = None) -> None:
        """Register a handler. entity=None means global trigger."""
        self._triggers[event_type][entity].append(callback)

    def unsubscribe(self, event_type: type, callback: Callable, entity: Any = None) -> None:
        """Remove a handler."""
        handlers = self._triggers.get(event_type, {}).get(entity, [])
        if callback in handlers:
            handlers.remove(callback)

    def raise_event(self, event: Any, entity: Any = None) -> None:
        """Dispatch event to entity-specific handlers first, then global handlers.

        Handlers are snapshot-listed before iteration to safely handle
        subscribe/unsubscribe during dispatch.
        """
        event_type = type(event)
        trigger_map = self._triggers.get(event_type)
        if trigger_map is None:
            return

        # Entity-specific triggers first
        if entity is not None:
            for callback in list(trigger_map.get(entity, [])):
                callback(event)

        # Global triggers
        for callback in list(trigger_map.get(None, [])):
            callback(event)

    def clear(self) -> None:
        """Remove all subscriptions."""
        self._triggers.clear()
