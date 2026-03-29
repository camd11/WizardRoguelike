"""Game class — manages the full run: levels, SP, transitions, win/loss."""
from __future__ import annotations

from typing import Generator

from game.constants import Team
from game.core.actions import CastAction, MoveAction, PassAction
from game.core.level import Level
from game.core.rng import GameRNG
from game.core.unit import Unit
from game.crafting.spell_library import SpellLibrary
from game.generation.level_generator import GeneratedLevel, generate_level


class Game:
    """Top-level game state for a single run."""

    MAX_LEVELS = 5  # Vertical slice: 5 levels

    def __init__(self, seed: int | None = None) -> None:
        self.rng = GameRNG(seed=seed)
        self.seed = self.rng.seed

        # Player
        self.player = self._create_player()
        self.spell_library = SpellLibrary()

        # SP economy
        self.sp: int = 8  # Starting SP (enough for 2-3 spells)
        self.sp_per_level: int = 4  # SP gained per level cleared

        # Level tracking
        self.level_num: int = 0
        self.current_gen: GeneratedLevel | None = None
        self.current_level: Level | None = None
        self.turn_generator: Generator | None = None

        # State
        self.victory: bool = False
        self.defeat: bool = False
        self.game_over: bool = False
        self.in_shop: bool = True  # Start in shop before level 1

        # Stats
        self.total_turns: int = 0
        self.enemies_killed: int = 0

    def _create_player(self) -> Unit:
        player = Unit()
        player.name = "Wizard"
        player.team = Team.PLAYER
        player.max_hp = 120
        player.cur_hp = 120
        player.asset_name = "char/player"  # RW2 player sprite
        return player

    def start_level(self) -> GeneratedLevel:
        """Generate and start the next level."""
        self.level_num += 1
        difficulty = self.level_num
        level_seed = self.rng.randint(0, 2**32 - 1)

        # Reset player position but keep HP, spells, buffs
        if self.current_level and self.player in self.current_level.units:
            self.current_level.remove_unit(self.player)

        # Heal player between levels
        self.player.cur_hp = self.player.max_hp
        self.player.shields = 0

        # Reset spell charges
        for spell in self.player.spells:
            spell.cur_charges = spell.max_charges
            spell.cur_cool_down = 0

        gen_level = generate_level(
            difficulty=difficulty,
            player=self.player,
            seed=level_seed,
        )

        self.current_gen = gen_level
        self.current_level = gen_level.level
        self.turn_generator = self.current_level.iter_frame()
        self.in_shop = False

        # Advance to first player input
        self._advance_to_input()

        return gen_level

    def submit_action(self, action: MoveAction | CastAction | PassAction) -> dict:
        """Submit a player action and advance the game.

        Sends the action to the turn generator, then advances through
        spell animations and enemy turns until the next player input
        is needed (or the turn/level ends).
        """
        if self.turn_generator is None or self.game_over:
            return {"error": "No active level"}

        # Track enemies alive before action to detect kills
        enemies_before = set()
        if self.current_level:
            enemies_before = {id(u) for u in self.current_level.units
                              if u.team == Team.ENEMY and u.is_alive()}

        # Send the action to the generator (resumes from the input yield)
        try:
            self.turn_generator.send(action)
        except StopIteration:
            pass

        # Advance through spell animations + enemy turns until next player input
        turn_complete = self._advance_to_input()

        if turn_complete:
            self.total_turns += 1

        # Detect killed enemies
        events = []
        if self.current_level:
            enemies_after = {id(u) for u in self.current_level.units
                             if u.team == Team.ENEMY and u.is_alive()}
            killed_ids = enemies_before - enemies_after
            self.enemies_killed += len(killed_ids)
            if killed_ids:
                events.append(f"{len(killed_ids)} enemy(ies) killed!")

        # Check win/loss conditions
        player_dead = not self.player.is_alive()
        level_clear = self.current_level.is_clear() if self.current_level else False

        if player_dead:
            self.defeat = True
            self.game_over = True
            events.append("You have been defeated!")

        if level_clear:
            events.append("Level cleared!")
            if self.level_num >= self.MAX_LEVELS:
                self.victory = True
                self.game_over = True
                events.append("Victory! You have conquered the rift!")
            else:
                self.sp += self.sp_per_level
                self.in_shop = True
                events.append(f"Gained {self.sp_per_level} SP. Total: {self.sp}")
                # Auto-save between levels
                from game.game.serialization import save_game
                save_game(self)
                events.append("Game saved.")

        return {
            "turn_complete": turn_complete,
            "level_clear": level_clear,
            "player_dead": player_dead,
            "enemies_remaining": self.current_level.enemies_remaining() if self.current_level else 0,
            "player_hp": self.player.cur_hp,
            "player_max_hp": self.player.max_hp,
            "events": events,
        }

    def buy_component(self, component_type: str, name: str) -> dict:
        """Buy a component from the shop.

        component_type: "element", "shape", or "modifier"
        """
        if not self.in_shop:
            return {"success": False, "error": "Not in shop"}

        if component_type == "element":
            cost = self.spell_library.buy_element(name, self.sp)
        elif component_type == "shape":
            cost = self.spell_library.buy_shape(name, self.sp)
        elif component_type == "modifier":
            cost = self.spell_library.buy_modifier(name, self.sp)
        else:
            return {"success": False, "error": f"Unknown component type: {component_type}"}

        if cost < 0:
            return {"success": False, "error": "Cannot afford or already owned"}

        self.sp -= cost
        return {"success": True, "cost": cost, "sp_remaining": self.sp}

    def craft_spell(self, element: str, shape: str,
                    modifiers: list[str] | None = None) -> dict:
        """Craft a spell and add it to the player."""
        spell = self.spell_library.craft_spell(element, shape, modifiers)
        if spell is None:
            can, errors = self.spell_library.can_craft(element, shape, modifiers)
            return {"success": False, "errors": errors}

        self.player.add_spell(spell)
        return {
            "success": True,
            "spell_name": spell.name,
            "damage": spell.damage,
            "range": spell.range,
            "charges": spell.max_charges,
        }

    def get_state(self) -> dict:
        """Get the full game state as a dict (for AI players / serialization)."""
        state = {
            "seed": self.seed,
            "level_num": self.level_num,
            "sp": self.sp,
            "victory": self.victory,
            "defeat": self.defeat,
            "game_over": self.game_over,
            "in_shop": self.in_shop,
            "total_turns": self.total_turns,
            "enemies_killed": self.enemies_killed,
            "player": {
                "name": self.player.name,
                "hp": self.player.cur_hp,
                "max_hp": self.player.max_hp,
                "x": self.player.x,
                "y": self.player.y,
                "shields": self.player.shields,
                "spells": [
                    {
                        "name": s.name,
                        "damage": s.damage,
                        "range": s.range,
                        "charges": s.cur_charges,
                        "max_charges": s.max_charges,
                        "cooldown": s.cur_cool_down,
                    }
                    for s in self.player.spells
                ],
                "buffs": [
                    {"name": b.name, "turns_left": b.turns_left}
                    for b in self.player.buffs
                ],
            },
            "library": {
                "owned_elements": sorted(self.spell_library.owned_elements),
                "owned_shapes": sorted(self.spell_library.owned_shapes),
                "owned_modifiers": sorted(self.spell_library.owned_modifiers),
            },
        }

        if self.current_level and not self.in_shop:
            state["level"] = {
                "width": self.current_level.width,
                "height": self.current_level.height,
                "turn_no": self.current_level.turn_no,
                "enemies_remaining": self.current_level.enemies_remaining(),
                "units": [
                    {
                        "name": u.name,
                        "team": u.team.name,
                        "hp": u.cur_hp,
                        "max_hp": u.max_hp,
                        "x": u.x,
                        "y": u.y,
                        "is_player": u.is_player(),
                    }
                    for u in self.current_level.units
                    if u.is_alive()
                ],
            }

        return state

    def _advance_to_input(self) -> bool:
        """Advance the turn generator until it needs player input.

        Returns True if at least one full turn completed during advancement.
        Keeps advancing past turn boundaries until reaching a player input yield.
        """
        if self.turn_generator is None:
            return False

        turn_completed = False
        max_steps = 5000  # Safety valve
        for _ in range(max_steps):
            # Check if waiting for player input
            if self.current_level and self.current_level.is_awaiting_input:
                return turn_completed

            # Check if player died
            if not self.player.is_alive():
                return True

            # Check if level is clear (no more enemies = no more turns needed)
            if self.current_level and self.current_level.is_clear():
                return True

            try:
                result = next(self.turn_generator)
                if result is True:
                    turn_completed = True
            except StopIteration:
                return True
