"""Tests for save/load system."""
import tempfile
from pathlib import Path
from unittest.mock import patch

from game.game.game_state import Game
from game.game.serialization import save_game, load_game, restore_game, SAVE_DIR


class TestSaveLoad:
    def test_save_creates_file(self):
        game = Game(seed=42)
        game.buy_component("element", "Fire")
        game.buy_component("shape", "Bolt")
        game.craft_spell("Fire", "Bolt")

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("game.game.serialization.SAVE_DIR", Path(tmpdir)):
                path = save_game(game, slot=0)
                assert path.exists()

    def test_save_and_restore(self):
        game = Game(seed=42)
        game.buy_component("element", "Fire")
        game.buy_component("element", "Ice")
        game.buy_component("shape", "Bolt")
        game.craft_spell("Fire", "Bolt")
        game.craft_spell("Ice", "Bolt")
        game.enemies_killed = 5
        game.total_turns = 20
        game.level_num = 2
        game.sp = 7

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("game.game.serialization.SAVE_DIR", Path(tmpdir)):
                save_game(game, slot=0)
                data = load_game(slot=0)
                assert data is not None

                restored = restore_game(data)
                assert restored.seed == game.seed
                assert restored.level_num == 2
                assert restored.sp == 7
                assert restored.enemies_killed == 5
                assert restored.total_turns == 20
                assert "Fire" in restored.spell_library.owned_elements
                assert "Ice" in restored.spell_library.owned_elements
                assert "Bolt" in restored.spell_library.owned_shapes
                assert len(restored.player.spells) == 2
                spell_names = {s.name for s in restored.player.spells}
                assert "Fire Bolt" in spell_names
                assert "Ice Bolt" in spell_names

    def test_load_nonexistent_returns_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("game.game.serialization.SAVE_DIR", Path(tmpdir)):
                assert load_game(slot=99) is None
