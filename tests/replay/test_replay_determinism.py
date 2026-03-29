"""Test that replaying a recorded game produces identical results."""
import tempfile
from pathlib import Path

from game.core.actions import CastAction, MoveAction, PassAction
from game.game.game_state import Game
from tests.replay.recorder import ReplayRecorder
from tests.replay.replayer import ReplayReplayer
from tests.simulation.headless_bot import HeadlessBot


class TestReplayDeterminism:
    def test_record_and_replay_match(self):
        """Record a bot game, replay it, verify identical final state."""
        # Play and record
        seed = 42
        bot = HeadlessBot(seed=seed)
        recorder = ReplayRecorder(seed=seed)

        # Record shop phase
        bot.setup_build()
        for elem in ["Fire", "Ice"]:
            recorder.record_shop_action("buy", component_type="element", name=elem)
        for shape in ["Bolt", "Touch"]:
            recorder.record_shop_action("buy", component_type="shape", name=shape)
        recorder.record_shop_action("craft", element="Fire", shape="Bolt")
        recorder.record_shop_action("craft", element="Fire", shape="Touch")
        recorder.record_shop_action("craft", element="Ice", shape="Bolt")

        # Play through first level, recording actions
        bot.game.start_level()
        max_actions = 50
        actions_recorded = 0

        while not bot.game.game_over and actions_recorded < max_actions:
            if bot.game.in_shop:
                break

            state = bot.game.get_state()
            player = state["player"]
            level_data = state.get("level", {})

            if not level_data:
                action = PassAction()
            else:
                enemies = [u for u in level_data.get("units", [])
                           if not u["is_player"] and u["hp"] > 0]
                if enemies:
                    nearest = min(enemies, key=lambda e: abs(e["x"] - player["x"]) + abs(e["y"] - player["y"]))
                    # Try casting
                    cast_done = False
                    for i, spell in enumerate(bot.game.player.spells):
                        if spell.cur_charges > 0 and spell.can_cast(nearest["x"], nearest["y"]):
                            action = CastAction(spell=spell, x=nearest["x"], y=nearest["y"])
                            cast_done = True
                            break
                    if not cast_done:
                        dx = 0 if nearest["x"] == player["x"] else (1 if nearest["x"] > player["x"] else -1)
                        dy = 0 if nearest["y"] == player["y"] else (1 if nearest["y"] > player["y"] else -1)
                        action = MoveAction(x=player["x"] + dx, y=player["y"] + dy)
                else:
                    action = PassAction()

            turn = bot.game.current_level.turn_no if bot.game.current_level else 0
            recorder.record_action(turn, action)
            bot.game.submit_action(action)
            actions_recorded += 1

        original_state = bot.game.get_state()

        # Save and reload replay
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            recorder.save(f.name)
            replay_data = ReplayRecorder.load(f.name)

        # Replay
        replayer = ReplayReplayer(replay_data)
        replayer.setup()
        replayer.game.start_level()

        for i in range(len(replay_data["frames"])):
            if replayer.game.game_over:
                break
            replayer.replay_step(i)
            if replayer.game.in_shop:
                break

        replay_state = replayer.game.get_state()

        # Verify key state matches
        assert original_state["player"]["hp"] == replay_state["player"]["hp"]
        assert original_state["enemies_killed"] == replay_state["enemies_killed"]

        # Cleanup
        Path(f.name).unlink()

    def test_replay_save_load_roundtrip(self):
        """Verify replay file saves and loads correctly."""
        recorder = ReplayRecorder(seed=123)
        recorder.record_shop_action("buy", component_type="element", name="Fire")
        recorder.record_action(1, MoveAction(x=2, y=3))
        recorder.record_action(1, PassAction())

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            recorder.save(f.name)
            data = ReplayRecorder.load(f.name)

        assert data["seed"] == 123
        assert len(data["shop_commands"]) == 1
        assert len(data["frames"]) == 2
        assert data["frames"][0]["type"] == "move"
        assert data["frames"][1]["type"] == "pass"

        Path(f.name).unlink()
