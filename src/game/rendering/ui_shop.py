"""Clickable shop UI for buying components and crafting spells.

Three-column layout: Elements | Shapes | Modifiers
Bottom section: crafting preview + crafted spells list
Click to select components, click "Craft" to create spell.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from game.crafting.components import ELEMENTS, MODIFIERS, SHAPES
from game.crafting.recipe_validator import validate_recipe

if TYPE_CHECKING:
    from game.game.game_state import Game

# Layout constants
COL_BG = (20, 20, 28)
COL_PANEL = (30, 30, 40)
COL_BORDER = (60, 60, 80)
COL_TEXT = (200, 200, 200)
COL_DIM = (120, 120, 140)
COL_HIGHLIGHT = (255, 255, 200)
COL_OWNED = (80, 200, 80)
COL_SELECTED = (255, 220, 80)
COL_UNAFFORDABLE = (150, 60, 60)
COL_BUTTON = (60, 80, 120)
COL_BUTTON_HOVER = (80, 110, 160)
COL_BUTTON_DISABLED = (40, 40, 50)
COL_CRAFT_OK = (80, 200, 80)
COL_CRAFT_BAD = (200, 80, 80)

ITEM_H = 28
HEADER_H = 36


class ShopUI:
    """Clickable shop interface for component purchasing and spell crafting."""

    def __init__(self, screen_w: int, screen_h: int) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h

        # Selection state
        self.selected_element: str | None = None
        self.selected_shape: str | None = None
        self.selected_modifiers: list[str] = []

        # Hover state
        self.hover_item: str | None = None
        self.message: str = ""
        self.message_color: tuple[int, int, int] = COL_TEXT

        # Button rects (computed during draw)
        self._element_rects: dict[str, pygame.Rect] = {}
        self._shape_rects: dict[str, pygame.Rect] = {}
        self._modifier_rects: dict[str, pygame.Rect] = {}
        self._craft_button: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._start_button: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._mastery_rects: dict[str, tuple] = {}  # name -> (rect, mastery)

    def draw(self, screen: pygame.Surface, game: Game,
             font: pygame.font.Font, font_large: pygame.font.Font,
             font_small: pygame.font.Font) -> None:
        """Draw the full shop screen."""
        screen.fill(COL_BG)
        lib = game.spell_library
        col_w = self.screen_w // 3

        # Title
        if game.level_num > 0:
            title = f"Level {game.level_num} Complete!"
        else:
            title = "Prepare for Battle"
        _text(screen, title, self.screen_w // 2 - 100, 12, COL_HIGHLIGHT, font_large)
        _text(screen, f"SP: {game.sp}", self.screen_w // 2 - 30, 42, (255, 220, 100), font_large)

        y_start = 75

        # Column 1: Elements
        self._element_rects.clear()
        _text(screen, "ELEMENTS", 30, y_start, COL_HIGHLIGHT, font)
        y = y_start + HEADER_H
        for name in sorted(ELEMENTS.keys()):
            elem = ELEMENTS[name]
            owned = name in lib.owned_elements
            selected = name == self.selected_element
            affordable = game.sp >= elem.sp_cost or owned

            rect = pygame.Rect(10, y, col_w - 20, ITEM_H - 2)
            self._element_rects[name] = rect

            # Background
            if selected:
                pygame.draw.rect(screen, (60, 60, 20), rect)
                pygame.draw.rect(screen, COL_SELECTED, rect, 2)
            elif name == self.hover_item:
                pygame.draw.rect(screen, (35, 35, 45), rect)

            # Text
            if owned:
                color = COL_OWNED if not selected else COL_SELECTED
                label = f"  {name} [owned] d:{elem.base_damage}"
            elif affordable:
                color = COL_TEXT
                label = f"  {name} [{elem.sp_cost} SP] d:{elem.base_damage}"
            else:
                color = COL_UNAFFORDABLE
                label = f"  {name} [{elem.sp_cost} SP] d:{elem.base_damage}"

            _text(screen, label, rect.x + 4, rect.y + 4, color, font_small)
            y += ITEM_H

        # Column 2: Shapes
        self._shape_rects.clear()
        _text(screen, "SHAPES", col_w + 30, y_start, COL_HIGHLIGHT, font)
        y = y_start + HEADER_H
        for name in sorted(SHAPES.keys()):
            shape = SHAPES[name]
            owned = name in lib.owned_shapes
            selected = name == self.selected_shape
            affordable = game.sp >= shape.sp_cost or owned

            rect = pygame.Rect(col_w + 10, y, col_w - 20, ITEM_H - 2)
            self._shape_rects[name] = rect

            if selected:
                pygame.draw.rect(screen, (60, 60, 20), rect)
                pygame.draw.rect(screen, COL_SELECTED, rect, 2)
            elif name == self.hover_item:
                pygame.draw.rect(screen, (35, 35, 45), rect)

            if owned:
                color = COL_OWNED if not selected else COL_SELECTED
                label = f"  {name} [owned] r:{shape.base_range} c:{shape.base_charges}"
            elif affordable:
                color = COL_TEXT
                label = f"  {name} [{shape.sp_cost} SP] r:{shape.base_range} c:{shape.base_charges}"
            else:
                color = COL_UNAFFORDABLE
                label = f"  {name} [{shape.sp_cost} SP] r:{shape.base_range} c:{shape.base_charges}"

            _text(screen, label, rect.x + 4, rect.y + 4, color, font_small)
            y += ITEM_H

        # Column 3: Modifiers
        self._modifier_rects.clear()
        _text(screen, "MODIFIERS (0-2)", 2 * col_w + 30, y_start, COL_HIGHLIGHT, font)
        y = y_start + HEADER_H
        for name in sorted(MODIFIERS.keys()):
            mod = MODIFIERS[name]
            owned = name in lib.owned_modifiers
            selected = name in self.selected_modifiers
            affordable = game.sp >= mod.sp_cost or owned

            rect = pygame.Rect(2 * col_w + 10, y, col_w - 20, ITEM_H - 2)
            self._modifier_rects[name] = rect

            if selected:
                pygame.draw.rect(screen, (60, 60, 20), rect)
                pygame.draw.rect(screen, COL_SELECTED, rect, 2)
            elif name == self.hover_item:
                pygame.draw.rect(screen, (35, 35, 45), rect)

            if owned:
                color = COL_OWNED if not selected else COL_SELECTED
                label = f"  {name} [owned]"
            elif affordable:
                color = COL_TEXT
                label = f"  {name} [{mod.sp_cost} SP]"
            else:
                color = COL_UNAFFORDABLE
                label = f"  {name} [{mod.sp_cost} SP]"

            _text(screen, label, rect.x + 4, rect.y + 4, color, font_small)
            y += ITEM_H

        # Crafting preview
        preview_y = max(y_start + HEADER_H + 8 * ITEM_H + 20, self.screen_h // 2 + 20)
        self._draw_craft_preview(screen, game, font, font_small, preview_y)

        # Existing spells (left half)
        spells_y = preview_y + 100
        _text(screen, "YOUR SPELLS:", 30, spells_y, COL_HIGHLIGHT, font)
        sy = spells_y + 22
        if game.player.spells:
            for sp in game.player.spells[:8]:
                _text(screen, f"  {sp.name}  d:{sp.damage} r:{sp.range} c:{sp.max_charges}",
                      30, sy, COL_TEXT, font_small)
                sy += 16
        else:
            _text(screen, "  (none — craft a spell first!)", 30, sy, COL_DIM, font_small)

        # Masteries (right half)
        self._mastery_rects.clear()
        mastery_y = spells_y
        mx = self.screen_w // 2 + 20
        _text(screen, "MASTERIES:", mx, mastery_y, COL_HIGHLIGHT, font)
        mastery_y += 22
        if hasattr(game, 'mastery_tracker'):
            available = game.mastery_tracker.get_available(
                game.spell_library.owned_elements,
                game.spell_library.owned_shapes,
            )
            for m in available[:8]:
                affordable = game.sp >= m.sp_cost
                col = COL_TEXT if affordable else COL_UNAFFORDABLE
                bonuses_str = ", ".join(f"+{v} {k}" for k, v in m.bonuses.items())
                label = f"  {m.name} [{m.sp_cost} SP] {bonuses_str}"
                rect = pygame.Rect(mx, mastery_y, col_w - 20, ITEM_H - 2)
                self._mastery_rects[m.name] = (rect, m)
                if m.name == self.hover_item:
                    pygame.draw.rect(screen, (35, 35, 45), rect)
                _text(screen, label, rect.x + 4, rect.y + 4, col, font_small)
                mastery_y += ITEM_H

        # Start button
        btn_w, btn_h = 200, 40
        btn_x = self.screen_w // 2 - btn_w // 2
        btn_y = self.screen_h - 60
        self._start_button = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        has_spells = len(game.player.spells) > 0
        btn_col = COL_BUTTON if has_spells else COL_BUTTON_DISABLED
        pygame.draw.rect(screen, btn_col, self._start_button, border_radius=6)
        pygame.draw.rect(screen, COL_BORDER, self._start_button, 2, border_radius=6)
        label = "START LEVEL" if has_spells else "CRAFT A SPELL FIRST"
        _text(screen, label, btn_x + btn_w // 2 - len(label) * 4, btn_y + 10,
              COL_TEXT if has_spells else COL_DIM, font)

        # Message
        if self.message:
            _text(screen, self.message, 30, self.screen_h - 90, self.message_color, font_small)

    def _draw_craft_preview(self, screen: pygame.Surface, game: Game,
                            font: pygame.font.Font, font_small: pygame.font.Font,
                            y: int) -> None:
        """Draw crafting preview showing what would be created."""
        pygame.draw.line(screen, COL_BORDER, (20, y - 5), (self.screen_w - 20, y - 5))

        if not self.selected_element or not self.selected_shape:
            _text(screen, "Click an Element + Shape to craft a spell", 30, y, COL_DIM, font_small)
            self._craft_button = pygame.Rect(0, 0, 0, 0)
            return

        elem = ELEMENTS[self.selected_element]
        shape = SHAPES[self.selected_shape]
        mods = [MODIFIERS[m] for m in self.selected_modifiers]

        result = validate_recipe(elem, shape, mods)
        mod_str = " + ".join(self.selected_modifiers) if self.selected_modifiers else "none"
        preview_name = f"{' '.join(self.selected_modifiers)} {self.selected_element} {self.selected_shape}".strip()

        _text(screen, f"Preview: {preview_name}", 30, y, COL_HIGHLIGHT, font)
        _text(screen, f"Modifiers: {mod_str}", 30, y + 20, COL_TEXT, font_small)

        if result.valid:
            # Calculate cost
            sp_needed = 0
            if self.selected_element not in game.spell_library.owned_elements:
                sp_needed += elem.sp_cost
            if self.selected_shape not in game.spell_library.owned_shapes:
                sp_needed += shape.sp_cost
            for m in self.selected_modifiers:
                if m not in game.spell_library.owned_modifiers:
                    sp_needed += MODIFIERS[m].sp_cost

            can_afford = game.sp >= sp_needed
            cost_str = f"Cost: {sp_needed} SP" if sp_needed > 0 else "Cost: FREE (components owned)"
            cost_col = COL_CRAFT_OK if can_afford else COL_CRAFT_BAD
            _text(screen, cost_str, 30, y + 36, cost_col, font_small)

            # Craft button
            btn = pygame.Rect(self.screen_w // 2 + 100, y + 10, 140, 32)
            self._craft_button = btn
            col = COL_BUTTON if can_afford else COL_BUTTON_DISABLED
            pygame.draw.rect(screen, col, btn, border_radius=4)
            pygame.draw.rect(screen, COL_BORDER, btn, 2, border_radius=4)
            _text(screen, "CRAFT SPELL", btn.x + 16, btn.y + 6,
                  COL_TEXT if can_afford else COL_DIM, font)
        else:
            _text(screen, f"Invalid: {result.errors[0]}", 30, y + 36, COL_CRAFT_BAD, font_small)
            self._craft_button = pygame.Rect(0, 0, 0, 0)

    def handle_click(self, mx: int, my: int, game: Game) -> str | None:
        """Handle a mouse click. Returns 'start_level' if start button clicked."""
        # Check element clicks
        for name, rect in self._element_rects.items():
            if rect.collidepoint(mx, my):
                if name == self.selected_element:
                    self.selected_element = None
                else:
                    self.selected_element = name
                    # Auto-buy if not owned and affordable
                    if name not in game.spell_library.owned_elements:
                        result = game.buy_component("element", name)
                        if result.get("success"):
                            self.message = f"Bought {name}!"
                            self.message_color = COL_OWNED
                        elif game.sp < ELEMENTS[name].sp_cost:
                            self.message = f"Can't afford {name} ({ELEMENTS[name].sp_cost} SP)"
                            self.message_color = COL_CRAFT_BAD
                            self.selected_element = None
                return None

        # Check shape clicks
        for name, rect in self._shape_rects.items():
            if rect.collidepoint(mx, my):
                if name == self.selected_shape:
                    self.selected_shape = None
                else:
                    self.selected_shape = name
                    if name not in game.spell_library.owned_shapes:
                        result = game.buy_component("shape", name)
                        if result.get("success"):
                            self.message = f"Bought {name}!"
                            self.message_color = COL_OWNED
                        elif game.sp < SHAPES[name].sp_cost:
                            self.message = f"Can't afford {name} ({SHAPES[name].sp_cost} SP)"
                            self.message_color = COL_CRAFT_BAD
                            self.selected_shape = None
                return None

        # Check modifier clicks (toggle)
        for name, rect in self._modifier_rects.items():
            if rect.collidepoint(mx, my):
                if name in self.selected_modifiers:
                    self.selected_modifiers.remove(name)
                elif len(self.selected_modifiers) < 2:
                    # Auto-buy
                    if name not in game.spell_library.owned_modifiers:
                        result = game.buy_component("modifier", name)
                        if result.get("success"):
                            self.message = f"Bought {name}!"
                            self.message_color = COL_OWNED
                        elif game.sp < MODIFIERS[name].sp_cost:
                            self.message = f"Can't afford {name}"
                            self.message_color = COL_CRAFT_BAD
                            return None
                    self.selected_modifiers.append(name)
                else:
                    self.message = "Max 2 modifiers"
                    self.message_color = COL_CRAFT_BAD
                return None

        # Check craft button
        if self._craft_button.collidepoint(mx, my):
            if self.selected_element and self.selected_shape:
                mods = self.selected_modifiers if self.selected_modifiers else None
                result = game.craft_spell(self.selected_element, self.selected_shape, mods)
                if result.get("success"):
                    self.message = f"Crafted {result['spell_name']}!"
                    self.message_color = COL_CRAFT_OK
                    self.selected_element = None
                    self.selected_shape = None
                    self.selected_modifiers = []
                else:
                    self.message = f"Failed: {result.get('errors', ['?'])[0]}"
                    self.message_color = COL_CRAFT_BAD
            return None

        # Check mastery clicks
        for name, (rect, mastery) in self._mastery_rects.items():
            if rect.collidepoint(mx, my):
                result = game.buy_mastery(name)
                if result.get("success"):
                    self.message = f"Learned {name}!"
                    self.message_color = COL_CRAFT_OK
                else:
                    self.message = result.get("error", "Cannot learn mastery")
                    self.message_color = COL_CRAFT_BAD
                return None

        # Check start button
        if self._start_button.collidepoint(mx, my) and game.player.spells:
            return "start_level"

        return None

    def handle_motion(self, mx: int, my: int) -> None:
        """Update hover state."""
        self.hover_item = None
        for name, rect in {**self._element_rects, **self._shape_rects, **self._modifier_rects}.items():
            if rect.collidepoint(mx, my):
                self.hover_item = name
                return
        for name, (rect, _) in self._mastery_rects.items():
            if rect.collidepoint(mx, my):
                self.hover_item = name
                return


def _text(screen: pygame.Surface, text: str, x: int, y: int,
          color: tuple[int, int, int], font: pygame.font.Font) -> None:
    surf = font.render(text, True, color)
    screen.blit(surf, (x, y))
