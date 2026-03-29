"""Simulation tests: headless bot plays full runs without crashing."""
import pytest

from tests.simulation.headless_bot import HeadlessBot


class TestHeadlessBotRun:
    def test_single_run_completes(self):
        """Bot must complete a full run (seed=42) without crashing."""
        bot = HeadlessBot(seed=42)
        result = bot.play_full_run(max_turns=300)
        assert result["turns_played"] > 0
        assert result["victory"] or result["defeat"] or result["turns_played"] >= 300

    def test_bot_kills_some_enemies(self):
        """Bot should kill at least a few enemies."""
        bot = HeadlessBot(seed=42)
        result = bot.play_full_run(max_turns=300)
        assert result["enemies_killed"] > 0

    @pytest.mark.slow
    @pytest.mark.parametrize("seed", range(10))
    def test_ten_seed_sweep(self, seed):
        """Run 10 seeds and verify none crash."""
        bot = HeadlessBot(seed=seed)
        result = bot.play_full_run(max_turns=300)
        assert result["turns_played"] > 0
        # Either won or lost — no hang
        assert result["victory"] or result["defeat"] or result["turns_played"] >= 300
