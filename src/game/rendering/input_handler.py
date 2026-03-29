"""Input handler — converts keyboard/mouse events to game actions.

Keyboard layout modeled on RW2:
  - WASD / Arrow keys: movement
  - 1-9: select spell
  - Left click: cast selected spell at tile
  - Space: pass turn
  - Tab: cycle through enemies
  - Escape: cancel targeting / open menu
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from game.core.actions import CastAction, MoveAction, PassAction

if TYPE_CHECKING:
    from game.core.unit import Unit
    from game.game.game_state import Game
    from game.rendering.renderer import Renderer


# Direction keys → (dx, dy)
MOVE_KEYS = {
    pygame.K_w: (0, -1), pygame.K_UP: (0, -1),
    pygame.K_s: (0, 1), pygame.K_DOWN: (0, 1),
    pygame.K_a: (-1, 0), pygame.K_LEFT: (-1, 0),
    pygame.K_d: (1, 0), pygame.K_RIGHT: (1, 0),
    # Diagonals (numpad)
    pygame.K_KP7: (-1, -1), pygame.K_KP9: (1, -1),
    pygame.K_KP1: (-1, 1), pygame.K_KP3: (1, 1),
    # QEZC for diagonals
    pygame.K_q: (-1, -1), pygame.K_e: (1, -1),
    pygame.K_z: (-1, 1), pygame.K_c: (1, 1),
}

SPELL_KEYS = {
    pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2,
    pygame.K_4: 3, pygame.K_5: 4, pygame.K_6: 5,
    pygame.K_7: 6, pygame.K_8: 7, pygame.K_9: 8,
}


class InputHandler:
    """Processes pygame events and produces game actions."""

    def __init__(self) -> None:
        self.pending_action: MoveAction | CastAction | PassAction | None = None
        self.shop_input: str = ""
        self.shop_message: str = ""

    def process_level_events(self, events: list[pygame.event.Event],
                             game: Game, renderer: Renderer) -> None:
        """Process events during level gameplay."""
        player = game.player
        level = game.current_level
        if not level:
            return

        for event in events:
            if event.type == pygame.KEYDOWN:
                # Movement
                if event.key in MOVE_KEYS:
                    dx, dy = MOVE_KEYS[event.key]
                    self.pending_action = MoveAction(x=player.x + dx, y=player.y + dy)
                    renderer.clear_target_tiles()

                # Pass turn
                elif event.key == pygame.K_SPACE or event.key == pygame.K_KP5:
                    self.pending_action = PassAction()
                    renderer.clear_target_tiles()

                # Select spell
                elif event.key in SPELL_KEYS:
                    idx = SPELL_KEYS[event.key]
                    if idx < len(player.spells):
                        renderer.selected_spell_idx = idx
                        # Show targeting preview
                        spell = player.spells[idx]
                        if spell.can_pay_costs() and renderer.hover_tile:
                            tx, ty = renderer.hover_tile
                            tiles = spell.get_impacted_tiles(tx, ty)
                            renderer.set_target_tiles([(p.x, p.y) for p in tiles])
                        else:
                            renderer.clear_target_tiles()

                # Tab: auto-target nearest enemy
                elif event.key == pygame.K_TAB:
                    self._auto_target_enemy(player, level, renderer)

            elif event.type == pygame.MOUSEMOTION:
                mx, my = event.pos
                tx, ty = renderer.camera.screen_to_tile(mx, my)
                if level.in_bounds(tx, ty):
                    renderer.hover_tile = (tx, ty)
                    # Update targeting preview
                    if renderer.selected_spell_idx < len(player.spells):
                        spell = player.spells[renderer.selected_spell_idx]
                        if spell.can_pay_costs():
                            tiles = spell.get_impacted_tiles(tx, ty)
                            renderer.set_target_tiles([(p.x, p.y) for p in tiles])
                else:
                    renderer.hover_tile = None
                    renderer.clear_target_tiles()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Left click: cast selected spell
                mx, my = event.pos
                tx, ty = renderer.camera.screen_to_tile(mx, my)
                if level.in_bounds(tx, ty) and renderer.selected_spell_idx < len(player.spells):
                    spell = player.spells[renderer.selected_spell_idx]
                    if spell.can_cast(tx, ty) and spell.can_pay_costs():
                        self.pending_action = CastAction(spell=spell, x=tx, y=ty)
                        renderer.clear_target_tiles()

    def process_shop_events(self, events: list[pygame.event.Event],
                            game: Game, renderer: Renderer) -> bool:
        """Process events during shop phase. Returns True when player wants to start level."""
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if self.shop_input.strip():
                        self._process_shop_command(game, renderer)
                        self.shop_input = ""
                    else:
                        # Enter with no input = start level
                        if game.player.spells:
                            return True
                        else:
                            self.shop_message = "Craft at least one spell first!"
                elif event.key == pygame.K_BACKSPACE:
                    self.shop_input = self.shop_input[:-1]
                elif event.key == pygame.K_ESCAPE:
                    self.shop_input = ""
                elif event.unicode and event.unicode.isprintable():
                    self.shop_input += event.unicode
        return False

    def _process_shop_command(self, game: Game, renderer: Renderer) -> None:
        """Parse shop input like 'fire bolt' or 'ice burst empowered'."""
        parts = self.shop_input.strip().lower().split()
        if not parts:
            return

        from game.crafting.components import ELEMENTS, SHAPES, MODIFIERS

        # Match element
        elem_name = None
        shape_name = None
        mod_names = []

        for part in parts:
            matched = False
            for name in ELEMENTS:
                if name.lower() == part:
                    elem_name = name
                    matched = True
                    break
            if matched:
                continue
            for name in SHAPES:
                if name.lower() == part:
                    shape_name = name
                    matched = True
                    break
            if matched:
                continue
            for name in MODIFIERS:
                if name.lower() == part:
                    mod_names.append(name)
                    matched = True
                    break
            if not matched:
                # Try buying the component
                for name in ELEMENTS:
                    if name.lower().startswith(part):
                        result = game.buy_component("element", name)
                        if result.get("success"):
                            self.shop_message = f"Bought {name}! ({result['sp_remaining']} SP left)"
                            renderer.add_log(f"Bought element: {name}")
                            return
                for name in SHAPES:
                    if name.lower().startswith(part):
                        result = game.buy_component("shape", name)
                        if result.get("success"):
                            self.shop_message = f"Bought {name}! ({result['sp_remaining']} SP left)"
                            renderer.add_log(f"Bought shape: {name}")
                            return
                for name in MODIFIERS:
                    if name.lower().startswith(part):
                        result = game.buy_component("modifier", name)
                        if result.get("success"):
                            self.shop_message = f"Bought {name}! ({result['sp_remaining']} SP left)"
                            renderer.add_log(f"Bought modifier: {name}")
                            return

                self.shop_message = f"Unknown: '{part}'"
                return

        if elem_name and shape_name:
            # Auto-buy if not owned
            if elem_name not in game.spell_library.owned_elements:
                game.buy_component("element", elem_name)
            if shape_name not in game.spell_library.owned_shapes:
                game.buy_component("shape", shape_name)
            for mn in mod_names:
                if mn not in game.spell_library.owned_modifiers:
                    game.buy_component("modifier", mn)

            result = game.craft_spell(elem_name, shape_name, mod_names if mod_names else None)
            if result.get("success"):
                self.shop_message = f"Crafted {result['spell_name']}!"
                renderer.add_log(f"Crafted: {result['spell_name']}")
            else:
                self.shop_message = f"Can't craft: {result.get('errors', ['Unknown error'])}"
        elif elem_name:
            game.buy_component("element", elem_name)
            self.shop_message = f"Bought element: {elem_name}"
        elif shape_name:
            game.buy_component("shape", shape_name)
            self.shop_message = f"Bought shape: {shape_name}"
        else:
            self.shop_message = "Type 'element shape [modifier]' to craft, e.g. 'fire bolt'"

    def _auto_target_enemy(self, player: Unit, level, renderer: Renderer) -> None:
        """Target the nearest enemy with the selected spell."""
        if renderer.selected_spell_idx >= len(player.spells):
            return
        spell = player.spells[renderer.selected_spell_idx]
        target = spell.get_ai_target()
        if target:
            if spell.can_cast(target.x, target.y) and spell.can_pay_costs():
                self.pending_action = CastAction(spell=spell, x=target.x, y=target.y)

    def get_action(self) -> MoveAction | CastAction | PassAction | None:
        """Consume and return the pending action."""
        action = self.pending_action
        self.pending_action = None
        return action
