"""Smart headless bot with strategic build planning and tactical combat.

This bot:
1. Builds synergistic spell loadouts (not just Fire Bolt)
2. Prioritizes targets by threat level
3. Retreats when low HP
4. Uses AOE spells against clusters
5. Kites ranged enemies (stay at max range)
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from game.core.actions import CastAction, MoveAction, PassAction
from game.core.types import Point
from game.game.game_state import Game
from tests.replay.recorder import ReplayRecorder

if TYPE_CHECKING:
    from game.core.unit import Unit


# Build strategies — different spell loadouts to try
BUILD_STRATEGIES = [
    {
        "name": "Fire Mage",
        "elements": ["Fire"],
        "shapes": ["Bolt", "Burst"],
        "spells": [("Fire", "Bolt", []), ("Fire", "Burst", [])],
    },
    {
        "name": "Ice Sniper",
        "elements": ["Ice"],
        "shapes": ["Bolt", "Beam"],
        "spells": [("Ice", "Bolt", []), ("Ice", "Beam", [])],
    },
    {
        "name": "Lightning Caster",
        "elements": ["Lightning"],
        "shapes": ["Bolt", "Burst"],
        "spells": [("Lightning", "Bolt", []), ("Lightning", "Burst", [])],
    },
    {
        "name": "Poison Specialist",
        "elements": ["Poison", "Nature"],
        "shapes": ["Bolt", "Touch"],
        "spells": [("Poison", "Bolt", []), ("Nature", "Touch", [])],
    },
    {
        "name": "Multi-Element",
        "elements": ["Fire", "Ice", "Lightning"],
        "shapes": ["Bolt"],
        "spells": [("Fire", "Bolt", []), ("Ice", "Bolt", []), ("Lightning", "Bolt", [])],
    },
]


class SmartBot:
    """Strategically plays the game with build planning and tactical combat."""

    def __init__(self, seed: int = 42, strategy_idx: int | None = None,
                 record: bool = False) -> None:
        self.game = Game(seed=seed)
        self.recorder = ReplayRecorder(seed) if record else None
        self.actions_taken: list[str] = []
        self.turns_played: int = 0

        # Pick strategy based on seed if not specified
        if strategy_idx is None:
            strategy_idx = seed % len(BUILD_STRATEGIES)
        self.strategy = BUILD_STRATEGIES[strategy_idx]

    def setup_build(self) -> None:
        """Buy components and craft spells based on strategy."""
        # Buy elements
        for elem in self.strategy["elements"]:
            self.game.buy_component("element", elem)
            if self.recorder:
                self.recorder.record_shop_action("buy", component_type="element", name=elem)

        # Buy shapes
        for shape in self.strategy["shapes"]:
            self.game.buy_component("shape", shape)
            if self.recorder:
                self.recorder.record_shop_action("buy", component_type="shape", name=shape)

        # Craft spells
        for elem, shape, mods in self.strategy["spells"]:
            result = self.game.craft_spell(elem, shape, mods if mods else None)
            if self.recorder and result.get("success"):
                self.recorder.record_shop_action("craft", element=elem, shape=shape,
                                                  modifiers=mods)

    def play_full_run(self, max_turns: int = 500) -> dict:
        """Play a complete run with strategic decisions."""
        self.setup_build()

        while not self.game.game_over and self.turns_played < max_turns:
            if self.game.in_shop:
                self._shop_phase()
                self.game.start_level()

            result = self._play_turn()
            self.turns_played += 1

            if result.get("player_dead") or result.get("level_clear"):
                if self.game.game_over:
                    break

        return {
            "victory": self.game.victory,
            "defeat": self.game.defeat,
            "levels_completed": self.game.level_num - (0 if self.game.victory else 1),
            "turns_played": self.turns_played,
            "enemies_killed": self.game.enemies_killed,
            "seed": self.game.seed,
            "strategy": self.strategy["name"],
        }

    def _shop_phase(self) -> None:
        """Aggressively expand the build between levels."""
        sp = self.game.sp
        lib = self.game.spell_library
        from game.crafting.components import ELEMENTS, SHAPES, MODIFIERS

        # Priority 1: Buy Empowered modifier if we don't have it
        if "Empowered" not in lib.owned_modifiers and sp >= 1:
            result = self.game.buy_component("modifier", "Empowered")
            if result.get("success"):
                sp = result["sp_remaining"]
                # Re-craft main spell with Empowered
                for elem_name in lib.owned_elements:
                    for shape_name in lib.owned_shapes:
                        r = self.game.craft_spell(elem_name, shape_name, ["Empowered"])
                        if r.get("success"):
                            break

        # Priority 2: Buy more shapes
        for shape_name in ["Burst", "Beam", "Touch", "Cone"]:
            if shape_name not in lib.owned_shapes and sp >= SHAPES[shape_name].sp_cost:
                result = self.game.buy_component("shape", shape_name)
                if result.get("success"):
                    sp = result["sp_remaining"]
                    for elem_name in lib.owned_elements:
                        r = self.game.craft_spell(elem_name, shape_name)
                        if r.get("success"):
                            break
                    break  # One per level

        # Priority 3: Buy new elements
        for elem_name in ["Lightning", "Ice", "Fire", "Nature"]:
            if elem_name not in lib.owned_elements and sp >= ELEMENTS[elem_name].sp_cost:
                result = self.game.buy_component("element", elem_name)
                if result.get("success"):
                    sp = result["sp_remaining"]
                    for shape_name in lib.owned_shapes:
                        r = self.game.craft_spell(elem_name, shape_name)
                        if r.get("success"):
                            break
                    break

        # Priority 4: Buy Extended or Piercing modifier
        for mod_name in ["Extended", "Piercing"]:
            if mod_name not in lib.owned_modifiers and sp >= MODIFIERS[mod_name].sp_cost:
                result = self.game.buy_component("modifier", mod_name)
                if result.get("success"):
                    sp = result["sp_remaining"]
                    break

        # Priority 5: Buy masteries if affordable
        if hasattr(self.game, 'mastery_tracker'):
            available = self.game.mastery_tracker.get_available(
                lib.owned_elements, lib.owned_shapes
            )
            for mastery in available:
                if self.game.sp >= mastery.sp_cost:
                    self.game.buy_mastery(mastery.name)
                    break  # One mastery per level

    def _play_turn(self) -> dict:
        """Tactical turn: prioritize threats, use positioning, manage resources."""
        state = self.game.get_state()
        player = state["player"]
        level_data = state.get("level", {})

        if not level_data:
            return self._submit(PassAction())

        enemies = [u for u in level_data.get("units", [])
                    if not u["is_player"] and u["hp"] > 0]

        if not enemies:
            return self._submit(PassAction())

        px, py = player["x"], player["y"]
        hp_pct = player["hp"] / max(1, player["max_hp"])

        # USE CONSUMABLES when needed
        if hasattr(self.game, 'consumables'):
            items = self.game.consumables.get_items()
            # Use healing potion when below 40% HP
            if hp_pct < 0.40:
                for i, c in enumerate(items):
                    if "Healing" in c.name or "Shield" in c.name:
                        self.game.consumables.use(i, self.game.player, self.game.current_level)
                        return self._submit(PassAction())  # Using consumable costs turn

        # Score enemies by threat (closer + higher damage = higher threat)
        def threat_score(e):
            dist = max(abs(e["x"] - px), abs(e["y"] - py))
            return -dist  # Closer = higher priority

        enemies_sorted = sorted(enemies, key=threat_score, reverse=True)
        nearest = enemies_sorted[0]
        nearest_dist = max(abs(nearest["x"] - px), abs(nearest["y"] - py))

        # LOW HP: try to retreat (move away from nearest enemy)
        if hp_pct < 0.25 and nearest_dist <= 2:
            retreat = self._get_retreat_move(px, py, nearest)
            if retreat:
                return self._submit(retreat)

        # TARGET LAIRS first (they spawn endless enemies)
        if self.game.current_level:
            from game.core.prop import Lair
            for x in range(self.game.current_level.width):
                for y in range(self.game.current_level.height):
                    tile = self.game.current_level.tiles[x][y]
                    if isinstance(tile.prop, Lair) and not tile.prop.destroyed:
                        # Try to cast at lair
                        for i, spell_data in enumerate(player["spells"]):
                            if spell_data["charges"] <= 0 or spell_data["cooldown"] > 0:
                                continue
                            spell = self.game.player.spells[i]
                            if spell.can_cast(x, y) and spell.can_pay_costs():
                                return self._submit(CastAction(spell=spell, x=x, y=y))
                        break  # Only try first lair found

        # Find best spell to cast
        best_spell = None
        best_target = None
        best_score = -1

        for i, spell_data in enumerate(player["spells"]):
            if spell_data["charges"] <= 0 or spell_data["cooldown"] > 0:
                continue
            spell = self.game.player.spells[i]

            # Try each enemy as target
            for enemy in enemies_sorted:
                if not spell.can_cast(enemy["x"], enemy["y"]):
                    continue
                if not spell.can_pay_costs():
                    continue

                # Score: damage efficiency + kills bonus
                score = spell_data["damage"]
                # Bonus for killing (overkill waste is bad)
                if spell_data["damage"] >= enemy["hp"]:
                    score += 20  # Kill bonus
                # Burst spells get bonus for clusters
                tiles = spell.get_impacted_tiles(enemy["x"], enemy["y"])
                enemies_in_aoe = sum(1 for e in enemies
                                      if any(t.x == e["x"] and t.y == e["y"] for t in tiles))
                score += enemies_in_aoe * 10

                if score > best_score:
                    best_score = score
                    best_spell = spell
                    best_target = (enemy["x"], enemy["y"])

        if best_spell and best_target:
            return self._submit(CastAction(spell=best_spell, x=best_target[0], y=best_target[1]))

        # No spell available — move toward nearest enemy, but stay at range if we have ranged spells
        has_ranged = any(s["range"] > 2 and s["charges"] > 0 for s in player["spells"])
        if has_ranged and nearest_dist <= 1:
            # Already adjacent but have ranged spells — might want to back off
            # But only if we have no melee spells with charges
            has_melee = any(s["range"] <= 1 and s["charges"] > 0 for s in player["spells"])
            if not has_melee:
                retreat = self._get_retreat_move(px, py, nearest)
                if retreat:
                    return self._submit(retreat)

        # Move toward nearest enemy
        dx = 0 if nearest["x"] == px else (1 if nearest["x"] > px else -1)
        dy = 0 if nearest["y"] == py else (1 if nearest["y"] > py else -1)
        return self._submit(MoveAction(x=px + dx, y=py + dy))

    def _get_retreat_move(self, px: int, py: int, enemy: dict) -> MoveAction | None:
        """Move away from an enemy."""
        dx = 0 if enemy["x"] == px else (-1 if enemy["x"] > px else 1)
        dy = 0 if enemy["y"] == py else (-1 if enemy["y"] > py else 1)
        target_x = px + dx
        target_y = py + dy

        if self.game.current_level and self.game.current_level.in_bounds(target_x, target_y):
            tile = self.game.current_level.tiles[target_x][target_y]
            if tile.can_walk():
                return MoveAction(x=target_x, y=target_y)
        return None

    def _submit(self, action) -> dict:
        """Submit action with optional recording."""
        if self.recorder and self.game.current_level:
            self.recorder.record_action(self.game.current_level.turn_no, action)
        return self.game.submit_action(action)
