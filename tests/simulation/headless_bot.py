"""Headless bot that plays full games via the Game API.

This is the foundation for Claude Code as an automated playtester.
The bot makes simple decisions: buy Fire+Bolt, craft it, and
target the nearest enemy each turn.
"""
from __future__ import annotations

from game.core.actions import CastAction, MoveAction, PassAction
from game.core.types import Point
from game.game.game_state import Game


class HeadlessBot:
    """AI bot that plays the game through the Game API."""

    def __init__(self, seed: int = 42) -> None:
        self.game = Game(seed=seed)
        self.actions_taken: list[str] = []
        self.turns_played: int = 0

    def setup_build(self) -> None:
        """Buy components and craft initial spells."""
        # Buy Fire + Bolt + Burst (basic loadout)
        self.game.buy_component("element", "Fire")
        self.game.buy_component("element", "Ice")
        self.game.buy_component("shape", "Bolt")
        self.game.buy_component("shape", "Touch")
        self.game.craft_spell("Fire", "Bolt")
        self.game.craft_spell("Fire", "Touch")
        self.game.craft_spell("Ice", "Bolt")

    def play_full_run(self, max_turns: int = 500) -> dict:
        """Play a complete run. Returns summary stats."""
        self.setup_build()

        while not self.game.game_over and self.turns_played < max_turns:
            if self.game.in_shop:
                # Between levels: maybe buy more components
                self._shop_phase()
                self.game.start_level()

            result = self._play_turn()
            self.turns_played += 1

            if result.get("player_dead"):
                break
            if result.get("level_clear"):
                if self.game.game_over:
                    break

        return {
            "victory": self.game.victory,
            "defeat": self.game.defeat,
            "levels_completed": self.game.level_num - (0 if self.game.victory else 1),
            "turns_played": self.turns_played,
            "enemies_killed": self.game.enemies_killed,
            "seed": self.game.seed,
        }

    def _shop_phase(self) -> None:
        """Buy components between levels if we can afford them."""
        # Try to expand element collection
        for elem in ["Lightning", "Dark", "Nature"]:
            if elem not in self.game.spell_library.owned_elements:
                result = self.game.buy_component("element", elem)
                if result.get("success"):
                    # Craft a bolt with the new element
                    if "Bolt" in self.game.spell_library.owned_shapes:
                        self.game.craft_spell(elem, "Bolt")
                    break

    def _play_turn(self) -> dict:
        """Play a single turn by picking the best action."""
        state = self.game.get_state()
        player = state["player"]
        level_data = state.get("level", {})

        if not level_data:
            return self.game.submit_action(PassAction())

        # Find nearest enemy
        enemies = [u for u in level_data.get("units", [])
                    if not u["is_player"] and u["hp"] > 0]

        if not enemies:
            return self.game.submit_action(PassAction())

        nearest = min(enemies, key=lambda e: abs(e["x"] - player["x"]) + abs(e["y"] - player["y"]))
        dist = max(abs(nearest["x"] - player["x"]), abs(nearest["y"] - player["y"]))

        # Try to cast a spell at the nearest enemy
        for spell_data in player["spells"]:
            spell_idx = player["spells"].index(spell_data)
            if spell_data["charges"] <= 0 or spell_data["cooldown"] > 0:
                continue

            spell = self.game.player.spells[spell_idx]
            if spell.can_cast(nearest["x"], nearest["y"]) and spell.can_pay_costs():
                action = CastAction(spell=spell, x=nearest["x"], y=nearest["y"])
                self.actions_taken.append(f"Cast {spell.name} at ({nearest['x']},{nearest['y']})")
                return self.game.submit_action(action)

        # No spell available — move toward nearest enemy
        if dist > 1:
            dx = 0 if nearest["x"] == player["x"] else (1 if nearest["x"] > player["x"] else -1)
            dy = 0 if nearest["y"] == player["y"] else (1 if nearest["y"] > player["y"] else -1)
            target_x = player["x"] + dx
            target_y = player["y"] + dy

            action = MoveAction(x=target_x, y=target_y)
            self.actions_taken.append(f"Move to ({target_x},{target_y})")
            return self.game.submit_action(action)

        # Adjacent but can't cast — pass
        self.actions_taken.append("Pass")
        return self.game.submit_action(PassAction())
