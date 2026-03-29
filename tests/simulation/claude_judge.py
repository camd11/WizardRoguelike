"""Claude Code judge for evaluating game runs.

Uses `claude -p` subprocess (subscription auth, NOT paid API) to evaluate
completed runs for balance and fun. Based on the judge pattern from
the 4-permutation pipeline (poc_penis_cum_combined.py).

Evaluates:
- Build viability: was the spell loadout effective?
- Balance: were any combos overpowered or underpowered?
- Interesting decisions: did the run have meaningful tactical choices?
- Difficulty curve: was the progression satisfying?
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def evaluate_run(run_data: dict, model: str = "sonnet") -> dict:
    """Evaluate a completed game run using Claude CLI.

    Args:
        run_data: dict with keys: victory, defeat, levels_completed, turns_played,
                  enemies_killed, seed, strategy, spell_names, per_level_stats
        model: Claude model to use ("sonnet" or "haiku")

    Returns:
        dict with: rating (1-10), analysis, balance_issues, suggestions
    """
    prompt = _build_judge_prompt(run_data)

    try:
        result = _call_claude(prompt, model)
        return _parse_judge_response(result)
    except Exception as e:
        return {
            "rating": -1,
            "analysis": f"Judge error: {e}",
            "balance_issues": [],
            "suggestions": [],
        }


def evaluate_balance_batch(runs: list[dict], model: str = "sonnet") -> dict:
    """Evaluate a batch of runs for overall balance assessment.

    Args:
        runs: list of run_data dicts
        model: Claude model to use

    Returns:
        dict with: overall_rating, analysis, broken_combos, weak_combos,
                   difficulty_assessment, recommendations
    """
    prompt = _build_batch_prompt(runs)

    try:
        result = _call_claude(prompt, model)
        return _parse_batch_response(result)
    except Exception as e:
        return {
            "overall_rating": -1,
            "analysis": f"Judge error: {e}",
            "recommendations": [],
        }


def _call_claude(prompt: str, model: str = "sonnet") -> str:
    """Call Claude CLI via subprocess.

    Strips ANTHROPIC_API_KEY and CLAUDE_CODE from env so it uses
    subscription auth (not paid API credits).
    """
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("CLAUDE_CODE", None)

    cmd = ["claude", "-p", prompt, "--model", model]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Claude CLI failed: {result.stderr[:200]}")

    return result.stdout.strip()


def _build_judge_prompt(run_data: dict) -> str:
    return f"""You are a game balance judge for a tactical roguelike called Wizard Roguelike.
The game has a spell crafting system: players combine Elements (Fire, Ice, Lightning, etc.)
with Shapes (Bolt, Burst, Beam, etc.) and Modifiers (Empowered, Extended, etc.) to create spells.
Players fight through 5 levels of increasing difficulty.

Evaluate this completed run:

**Run Summary:**
- Outcome: {"VICTORY" if run_data.get("victory") else "DEFEAT"}
- Levels completed: {run_data.get("levels_completed", 0)}/5
- Enemies killed: {run_data.get("enemies_killed", 0)}
- Turns played: {run_data.get("turns_played", 0)}
- Build strategy: {run_data.get("strategy", "unknown")}
- Spells used: {", ".join(run_data.get("spell_names", []))}
- Seed: {run_data.get("seed", "?")}

Respond in this EXACT JSON format (no other text):
{{
  "rating": <1-10 fun/balance score>,
  "analysis": "<2-3 sentence analysis of this run>",
  "balance_issues": ["<issue 1>", "<issue 2>"],
  "suggestions": ["<suggestion 1>", "<suggestion 2>"]
}}"""


def _build_batch_prompt(runs: list[dict]) -> str:
    run_summaries = []
    for i, r in enumerate(runs[:20]):  # Limit to 20 runs
        run_summaries.append(
            f"Run {i+1}: {'WIN' if r.get('victory') else 'LOSS'} | "
            f"Levels: {r.get('levels_completed', 0)}/5 | "
            f"Kills: {r.get('enemies_killed', 0)} | "
            f"Turns: {r.get('turns_played', 0)} | "
            f"Strategy: {r.get('strategy', '?')} | "
            f"Spells: {', '.join(r.get('spell_names', []))}"
        )

    runs_text = "\n".join(run_summaries)
    wins = sum(1 for r in runs if r.get("victory"))
    total = len(runs)

    return f"""You are a game balance judge for a tactical roguelike called Wizard Roguelike.
The game has a spell crafting system with 8 elements, 8 shapes, and 8 modifiers.
Players fight through 5 levels. Analyze these {total} automated bot runs:

**Win Rate: {wins}/{total} ({wins*100//max(1,total)}%)**

{runs_text}

Respond in this EXACT JSON format (no other text):
{{
  "overall_rating": <1-10>,
  "analysis": "<3-4 sentence overall balance assessment>",
  "broken_combos": ["<overpowered combo 1>"],
  "weak_combos": ["<underpowered combo 1>"],
  "difficulty_assessment": "<too easy / about right / too hard>",
  "recommendations": ["<balance change 1>", "<balance change 2>"]
}}"""


def _parse_judge_response(text: str) -> dict:
    """Parse JSON response from Claude."""
    # Find JSON in response (Claude sometimes adds surrounding text)
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return {
        "rating": -1,
        "analysis": text[:500],
        "balance_issues": [],
        "suggestions": [],
    }


def _parse_batch_response(text: str) -> dict:
    """Parse batch evaluation JSON response."""
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return {
        "overall_rating": -1,
        "analysis": text[:500],
        "recommendations": [],
    }


def run_balance_evaluation(num_seeds: int = 20, model: str = "sonnet") -> dict:
    """Run a full balance evaluation: play games with bot, then judge them.

    This is the main entry point for automated balance testing.
    """
    from tests.simulation.smart_bot import SmartBot, BUILD_STRATEGIES

    print(f"Running {num_seeds} seeds across {len(BUILD_STRATEGIES)} strategies...")
    runs = []
    for seed in range(num_seeds):
        for si, strat in enumerate(BUILD_STRATEGIES):
            bot = SmartBot(seed=seed * 100 + si, strategy_idx=si)
            result = bot.play_full_run(max_turns=300)
            result["spell_names"] = [s.name for s in bot.game.player.spells]
            runs.append(result)

    total = len(runs)
    wins = sum(1 for r in runs if r["victory"])
    print(f"Completed: {wins}/{total} victories ({wins*100//max(1,total)}%)")
    print(f"Submitting to Claude judge ({model})...")

    evaluation = evaluate_balance_batch(runs, model=model)

    print(f"\n=== BALANCE EVALUATION ===")
    print(f"Overall Rating: {evaluation.get('overall_rating', '?')}/10")
    print(f"Analysis: {evaluation.get('analysis', 'N/A')}")
    print(f"Difficulty: {evaluation.get('difficulty_assessment', 'N/A')}")
    if evaluation.get("broken_combos"):
        print(f"Broken combos: {evaluation['broken_combos']}")
    if evaluation.get("weak_combos"):
        print(f"Weak combos: {evaluation['weak_combos']}")
    if evaluation.get("recommendations"):
        print(f"Recommendations:")
        for rec in evaluation["recommendations"]:
            print(f"  - {rec}")

    return evaluation
