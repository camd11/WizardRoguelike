"""Replay replayer — re-executes recorded actions into a fresh Game.

Can be used headlessly for determinism testing, or with the Pygame renderer
for visual playback of AI games.
"""
from __future__ import annotations

from game.core.actions import CastAction, MoveAction, PassAction
from game.game.game_state import Game
from tests.replay.recorder import ReplayRecorder


class ReplayReplayer:
    """Replays a recorded game from a replay file or dict."""

    def __init__(self, replay_data: dict) -> None:
        self.seed = replay_data["seed"]
        self.shop_commands = replay_data["shop_commands"]
        self.frames = replay_data["frames"]
        self.game: Game | None = None

    def setup(self) -> Game:
        """Create a fresh Game and execute shop commands."""
        self.game = Game(seed=self.seed)

        # Replay shop commands
        for cmd in self.shop_commands:
            if cmd["type"] == "buy":
                self.game.buy_component(cmd["component_type"], cmd["name"])
            elif cmd["type"] == "craft":
                self.game.craft_spell(cmd["element"], cmd["shape"],
                                      cmd.get("modifiers"))

        return self.game

    def replay_all(self) -> dict:
        """Replay all frames headlessly. Returns final game state."""
        if self.game is None:
            self.setup()

        # Start first level
        if self.game.in_shop:
            self.game.start_level()

        for frame in self.frames:
            if self.game.game_over:
                break

            action = self._frame_to_action(frame)
            if action:
                self.game.submit_action(action)

            # Start next level if needed
            if self.game.in_shop and not self.game.game_over:
                self.game.start_level()

        return self.game.get_state()

    def replay_step(self, frame_idx: int) -> dict | None:
        """Replay a single frame. Returns the submit_action result."""
        if frame_idx >= len(self.frames) or self.game is None:
            return None

        frame = self.frames[frame_idx]
        action = self._frame_to_action(frame)
        if action and not self.game.game_over:
            return self.game.submit_action(action)
        return None

    def _frame_to_action(self, frame: dict) -> MoveAction | CastAction | PassAction | None:
        if frame["type"] == "move":
            return MoveAction(x=frame["data"]["x"], y=frame["data"]["y"])
        elif frame["type"] == "pass":
            return PassAction()
        elif frame["type"] == "cast":
            spell_idx = frame["data"]["spell_idx"]
            if spell_idx < len(self.game.player.spells):
                spell = self.game.player.spells[spell_idx]
                return CastAction(spell=spell, x=frame["data"]["x"], y=frame["data"]["y"])
        return None
