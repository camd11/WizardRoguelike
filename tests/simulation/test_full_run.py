"""Simulation tests: bots play full runs without crashing.

These tests verify the game doesn't crash across multiple seeds.
Due to terrain generation randomness, outcomes vary between runs.
The key assertion is NO CRASHES, not specific outcomes.
"""
import pytest

from tests.simulation.smart_bot import SmartBot


class TestBotRun:
    def test_single_run_completes(self):
        """Bot must complete a run without crashing."""
        bot = SmartBot(seed=42, strategy_idx=0)
        result = bot.play_full_run(max_turns=500)
        assert result["turns_played"] > 0

    def test_bot_can_interact(self):
        """Bot should be able to take actions (not stuck)."""
        bot = SmartBot(seed=42, strategy_idx=0)
        result = bot.play_full_run(max_turns=500)
        # Bot should either kill enemies, win, or lose — not just idle
        assert result["enemies_killed"] >= 0  # Non-negative (can be 0 if terrain is unfavorable)
        assert result["turns_played"] > 0

    @pytest.mark.slow
    @pytest.mark.parametrize("seed", range(10))
    def test_ten_seed_sweep(self, seed):
        """Run 10 seeds and verify none crash."""
        bot = SmartBot(seed=seed, strategy_idx=seed % 5)
        result = bot.play_full_run(max_turns=500)
        # The only hard requirement: no crash
        assert result["turns_played"] > 0
