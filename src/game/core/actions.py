"""Player/AI action types passed to Unit.advance()."""
from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from game.core.spell_base import Spell


class MoveAction(NamedTuple):
    """Move to an adjacent tile."""
    x: int
    y: int


class CastAction(NamedTuple):
    """Cast a spell at a target location."""
    spell: Spell
    x: int
    y: int


class PassAction(NamedTuple):
    """Skip turn."""
    pass
