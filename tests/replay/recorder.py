"""Replay recorder — captures game actions for deterministic replay.

Records seed + action sequence as JSON. Can be replayed headlessly
or visually through the Pygame renderer for watching AI play.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from game.core.actions import CastAction, MoveAction, PassAction


@dataclass
class ReplayFrame:
    """A single recorded action."""
    turn: int
    action_type: str  # "move", "cast", "pass"
    data: dict = field(default_factory=dict)


class ReplayRecorder:
    """Records game actions for deterministic replay."""

    def __init__(self, seed: int) -> None:
        self.seed = seed
        self.frames: list[ReplayFrame] = []
        self.shop_commands: list[dict] = []  # Component purchases + crafts

    def record_shop_action(self, action_type: str, **kwargs) -> None:
        """Record a shop action (buy component, craft spell)."""
        self.shop_commands.append({"type": action_type, **kwargs})

    def record_action(self, turn: int, action: MoveAction | CastAction | PassAction) -> None:
        """Record a player action."""
        if isinstance(action, MoveAction):
            self.frames.append(ReplayFrame(turn, "move", {"x": action.x, "y": action.y}))
        elif isinstance(action, CastAction):
            self.frames.append(ReplayFrame(turn, "cast", {
                "spell_name": action.spell.name,
                "spell_idx": action.spell.caster.spells.index(action.spell) if action.spell.caster else 0,
                "x": action.x, "y": action.y,
            }))
        elif isinstance(action, PassAction):
            self.frames.append(ReplayFrame(turn, "pass", {}))

    def save(self, path: str | Path) -> None:
        """Save replay to JSON file."""
        data = {
            "seed": self.seed,
            "shop_commands": self.shop_commands,
            "frames": [
                {"turn": f.turn, "type": f.action_type, "data": f.data}
                for f in self.frames
            ],
        }
        Path(path).write_text(json.dumps(data, indent=2))

    @staticmethod
    def load(path: str | Path) -> dict:
        """Load replay from JSON file."""
        return json.loads(Path(path).read_text())
