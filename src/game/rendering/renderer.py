"""Main renderer — composites tiles, units, effects, and UI.

Layout modeled on RW2:
  [Left Panel: Character info]  [Center: Level grid]  [Right Panel: Examine/Log]

RW2 uses a 1600×1024 window with left/right info panels flanking the tile grid.
We replicate this layout scaled to 32px tiles.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from game.constants import Tags, Team, TileType
from game.rendering.animation import AnimationManager
from game.rendering.asset_loader import AssetLoader, DISPLAY_TILE
from game.rendering.camera import Camera

if TYPE_CHECKING:
    from game.core.level import Level
    from game.core.unit import Unit
    from game.game.game_state import Game

# Colors matching RW2's palette
COL_BG = (15, 15, 20)
COL_PANEL_BG = (20, 20, 28)
COL_PANEL_BORDER = (60, 60, 80)
COL_TEXT = (200, 200, 200)
COL_TEXT_DIM = (120, 120, 140)
COL_TEXT_HIGHLIGHT = (255, 255, 200)
COL_HP_BAR = (180, 30, 30)
COL_HP_BAR_BG = (60, 20, 20)
COL_SHIELD = (100, 150, 255)
COL_TARGETING = (255, 255, 100, 80)
COL_EXIT = (100, 255, 100)
COL_ENEMY_HP = (200, 40, 40)
COL_ALLY_HP = (40, 200, 40)

SCREEN_W = 1280
SCREEN_H = 800
PANEL_W = 220
FONT_SIZE = 14
FONT_SIZE_LARGE = 18
FONT_SIZE_SMALL = 11


class Renderer:
    """Handles all Pygame drawing. Modeled on RW2's rendering approach."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.assets = AssetLoader()
        self.camera = Camera(SCREEN_W, SCREEN_H, PANEL_W, PANEL_W)
        self.anims = AnimationManager()

        # Fonts
        self.font = pygame.font.SysFont("monospace", FONT_SIZE)
        self.font_large = pygame.font.SysFont("monospace", FONT_SIZE_LARGE, bold=True)
        self.font_small = pygame.font.SysFont("monospace", FONT_SIZE_SMALL)

        # State
        self.show_help: bool = False
        self.hover_tile: tuple[int, int] | None = None
        self.selected_spell_idx: int = 0
        self.combat_log: list[str] = []
        self._target_tiles: list[tuple[int, int]] = []
        self._target_color: tuple[int, int, int] = (255, 255, 100)
        self._spell_range_data: tuple | None = None  # (cx, cy, range, color)

    def render_game(self, game: Game) -> None:
        """Render the full game screen (level mode)."""
        self.screen.fill(COL_BG)
        level = game.current_level
        if not level:
            return

        player = game.player
        self.camera.center_on(player.x, player.y)

        # Determine biome sprites
        biome = game.current_gen.biome if game.current_gen else None
        floor_spr = biome.floor_sprite if biome else "tiles/floor/stone"
        wall_spr = biome.wall_sprite if biome else "tiles/wall/stone"

        # Draw level grid
        self._draw_tiles(level, floor_spr, wall_spr)
        self._draw_targeting()
        self._draw_units(level)
        self._draw_effects()

        # Draw UI panels (RW2 style: left = character, right = examine/log)
        self._draw_left_panel(game)
        self._draw_right_panel(game)

        # Status bar at bottom
        self._draw_status_bar(game)

        # Help overlay
        if self.show_help:
            self._draw_help_overlay()

    def render_shop(self, game: Game) -> None:
        """Render the shop/crafting screen between levels."""
        self.screen.fill(COL_BG)
        self._draw_shop_screen(game)

    def render_game_over(self, game: Game) -> None:
        """Render victory or defeat screen."""
        self.screen.fill(COL_BG)
        if game.victory:
            title = "VICTORY"
            color = (100, 255, 100)
        else:
            title = "DEFEAT"
            color = (255, 60, 60)

        title_surf = self.font_large.render(title, True, color)
        self.screen.blit(title_surf, (SCREEN_W // 2 - title_surf.get_width() // 2, 200))

        stats = [
            f"Levels Cleared: {game.level_num}",
            f"Enemies Killed: {game.enemies_killed}",
            f"Total Turns: {game.total_turns}",
            f"Spells Crafted: {len(game.spell_library.crafted_spells)}",
            f"Equipment Found: {len(game.equipped)}",
            f"Seed: {game.seed}",
        ]

        # Spells used
        if game.player.spells:
            stats.append("")
            stats.append("Spells:")
            for s in game.player.spells[:6]:
                stats.append(f"  {s.name} (d:{s.damage} r:{s.range})")

        # Equipment
        if game.equipped:
            stats.append("")
            stats.append("Equipment:")
            for slot, eq in sorted(game.equipped.items()):
                stats.append(f"  {slot}: {eq.name}")

        # Combat log recap (last 5 entries)
        if self.combat_log:
            stats.append("")
            stats.append("Last Events:")
            for line in self.combat_log[-5:]:
                stats.append(f"  {line}")

        stats.extend(["", "Press SPACE to quit, R to restart"])

        for i, line in enumerate(stats):
            surf = self.font_small.render(line, True, COL_TEXT)
            self.screen.blit(surf, (SCREEN_W // 2 - surf.get_width() // 2, 260 + i * 18))

    # -------------------------------------------------------------------
    # Level rendering
    # -------------------------------------------------------------------
    def _draw_tiles(self, level: Level, floor_spr: str, wall_spr: str) -> None:
        # Compute FOV from player position for visibility dimming
        player = level.get_player()
        fov = None
        if player:
            fov = level.compute_fov(player.x, player.y)

        for x in range(level.width):
            for y in range(level.height):
                if not self.camera.is_visible(x, y):
                    continue
                sx, sy = self.camera.tile_to_screen(x, y)
                tile = level.tiles[x][y]

                if tile.is_wall:
                    spr = self.assets.get_wall_sprite(wall_spr)
                elif tile.is_chasm:
                    pygame.draw.rect(self.screen, (10, 10, 15), (sx, sy, DISPLAY_TILE, DISPLAY_TILE))
                    continue
                else:
                    spr = self.assets.get_floor_sprite(floor_spr)

                self.screen.blit(spr, (sx, sy))

                # Dim tiles outside FOV (explored but not currently visible)
                if fov is not None and not fov[x][y]:
                    dim = pygame.Surface((DISPLAY_TILE, DISPLAY_TILE), pygame.SRCALPHA)
                    dim.fill((0, 0, 0, 140))
                    self.screen.blit(dim, (sx, sy))

                # Draw props
                if tile.prop == "EXIT":
                    pygame.draw.rect(self.screen, COL_EXIT, (sx + 4, sy + 4, DISPLAY_TILE - 8, DISPLAY_TILE - 8), 2)
                elif hasattr(tile.prop, 'cur_hp') and hasattr(tile.prop, 'destroyed'):
                    # Lair rendering
                    from game.core.prop import Lair
                    if isinstance(tile.prop, Lair) and not tile.prop.destroyed:
                        # Red diamond for lair
                        half = DISPLAY_TILE // 2
                        pts = [(sx + half, sy + 2), (sx + DISPLAY_TILE - 2, sy + half),
                               (sx + half, sy + DISPLAY_TILE - 2), (sx + 2, sy + half)]
                        pygame.draw.polygon(self.screen, (200, 50, 50), pts)
                        pygame.draw.polygon(self.screen, (255, 80, 80), pts, 1)
                        # HP bar
                        hp_pct = tile.prop.cur_hp / max(1, tile.prop.max_hp)
                        bar_w = DISPLAY_TILE - 4
                        pygame.draw.rect(self.screen, (80, 20, 20), (sx + 2, sy + DISPLAY_TILE + 1, bar_w, 2))
                        pygame.draw.rect(self.screen, (200, 50, 50), (sx + 2, sy + DISPLAY_TILE + 1, int(bar_w * hp_pct), 2))

                # Draw cloud zones (semi-transparent color overlay)
                if tile.cloud and hasattr(tile.cloud, 'color'):
                    cloud_overlay = pygame.Surface((DISPLAY_TILE, DISPLAY_TILE), pygame.SRCALPHA)
                    cloud_color = tile.cloud.color if hasattr(tile.cloud, 'color') else (200, 100, 50)
                    cloud_overlay.fill((*cloud_color, 60))
                    self.screen.blit(cloud_overlay, (sx, sy))

    def _draw_targeting(self) -> None:
        """Draw targeting overlay with element-colored impacted tiles and range circle."""
        # Draw range circle for selected spell
        if self._spell_range_data:
            cx, cy, r, color = self._spell_range_data
            scx, scy = self.camera.tile_to_screen(cx, cy)
            center_px = scx + DISPLAY_TILE // 2
            center_py = scy + DISPLAY_TILE // 2
            radius_px = int(r * DISPLAY_TILE)
            if radius_px > 0:
                circle_surf = pygame.Surface((radius_px * 2 + 4, radius_px * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(circle_surf, (*color, 30), (radius_px + 2, radius_px + 2), radius_px)
                pygame.draw.circle(circle_surf, (*color, 60), (radius_px + 2, radius_px + 2), radius_px, 1)
                self.screen.blit(circle_surf, (center_px - radius_px - 2, center_py - radius_px - 2))

        # Draw impacted tiles
        if not self._target_tiles:
            return
        color = self._target_color
        overlay = pygame.Surface((DISPLAY_TILE, DISPLAY_TILE), pygame.SRCALPHA)
        overlay.fill((*color, 50))
        for tx, ty in self._target_tiles:
            sx, sy = self.camera.tile_to_screen(tx, ty)
            self.screen.blit(overlay, (sx, sy))

    def _draw_units(self, level: Level) -> None:
        for unit in level.units:
            if not unit.is_alive():
                continue
            if not self.camera.is_visible(unit.x, unit.y):
                continue
            sx, sy = self.camera.tile_to_screen(unit.x, unit.y)

            # Draw unit sprite
            spr = self.assets.get_unit_sprite(unit.asset_name)
            self.screen.blit(spr, (sx, sy))

            # HP bar underneath (RW2 shows small HP bars under enemies)
            if not unit.is_player():
                bar_w = DISPLAY_TILE
                bar_h = 3
                bar_y = sy + DISPLAY_TILE + 1
                hp_pct = unit.cur_hp / max(1, unit.max_hp)
                col = COL_ALLY_HP if unit.team == Team.PLAYER else COL_ENEMY_HP
                pygame.draw.rect(self.screen, COL_HP_BAR_BG, (sx, bar_y, bar_w, bar_h))
                pygame.draw.rect(self.screen, col, (sx, bar_y, int(bar_w * hp_pct), bar_h))

            # Buff icons (small colored dots above unit, like RW2 status icons)
            for i, buff in enumerate(unit.buffs[:6]):
                bx = sx + i * 6
                by = sy - 5
                pygame.draw.circle(self.screen, buff.color, (bx + 3, by + 3), 2)

    def _draw_effects(self) -> None:
        self.anims.update()

        # Projectile trails (draw first, behind other effects)
        for trail in self.anims.projectile_trails:
            sx, sy = self.camera.tile_to_screen(trail.x, trail.y)
            overlay = pygame.Surface((DISPLAY_TILE, DISPLAY_TILE), pygame.SRCALPHA)
            # Draw a small diamond/circle trail
            half = DISPLAY_TILE // 2
            pygame.draw.circle(overlay, (*trail.color, trail.alpha), (half, half), 4)
            self.screen.blit(overlay, (sx, sy))

        # Burst rings
        for ring in self.anims.burst_rings:
            sx, sy = self.camera.tile_to_screen(ring.x, ring.y)
            center_x = sx + DISPLAY_TILE // 2
            center_y = sy + DISPLAY_TILE // 2
            radius_px = ring.radius * DISPLAY_TILE
            if radius_px > 0:
                ring_surf = pygame.Surface((radius_px * 2 + 4, radius_px * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(ring_surf, (*ring.color, ring.alpha),
                                   (radius_px + 2, radius_px + 2), radius_px, 2)
                self.screen.blit(ring_surf,
                                 (center_x - radius_px - 2, center_y - radius_px - 2))

        # Tile flashes
        for flash in self.anims.tile_flashes:
            sx, sy = self.camera.tile_to_screen(flash.x, flash.y)
            overlay = pygame.Surface((DISPLAY_TILE, DISPLAY_TILE), pygame.SRCALPHA)
            overlay.fill((*flash.color, flash.alpha))
            self.screen.blit(overlay, (sx, sy))

        # Death effects (expanding red X)
        for death in self.anims.death_effects:
            sx, sy = self.camera.tile_to_screen(death.x, death.y)
            center_x = sx + DISPLAY_TILE // 2
            center_y = sy + DISPLAY_TILE // 2
            size = int(DISPLAY_TILE * death.scale / 2)
            death_surf = pygame.Surface((DISPLAY_TILE * 2, DISPLAY_TILE * 2), pygame.SRCALPHA)
            cx, cy = DISPLAY_TILE, DISPLAY_TILE
            pygame.draw.line(death_surf, (255, 40, 40, death.alpha),
                             (cx - size, cy - size), (cx + size, cy + size), 3)
            pygame.draw.line(death_surf, (255, 40, 40, death.alpha),
                             (cx + size, cy - size), (cx - size, cy + size), 3)
            self.screen.blit(death_surf, (center_x - DISPLAY_TILE, center_y - DISPLAY_TILE))

        # Damage numbers
        for dmg in self.anims.damage_numbers:
            sx, sy = self.camera.tile_to_screen(dmg.x, dmg.y)
            text = self.font_small.render(str(dmg.amount), True, dmg.color)
            text.set_alpha(dmg.alpha)
            self.screen.blit(text, (sx + 8, sy + dmg.y_offset))

    def set_target_tiles(self, tiles: list[tuple[int, int]],
                         color: tuple[int, int, int] = (255, 255, 100)) -> None:
        self._target_tiles = tiles
        self._target_color = color

    def set_spell_range(self, cx: int, cy: int, spell_range: int,
                        color: tuple[int, int, int] = (200, 200, 200)) -> None:
        self._spell_range_data = (cx, cy, spell_range, color)

    def clear_target_tiles(self) -> None:
        self._target_tiles = []
        self._spell_range_data = None

    # -------------------------------------------------------------------
    # Left panel (Character info — matches RW2's left panel)
    # -------------------------------------------------------------------
    def _draw_left_panel(self, game: Game) -> None:
        panel = pygame.Rect(0, 0, PANEL_W, SCREEN_H)
        pygame.draw.rect(self.screen, COL_PANEL_BG, panel)
        pygame.draw.line(self.screen, COL_PANEL_BORDER, (PANEL_W, 0), (PANEL_W, SCREEN_H))

        y = 10
        player = game.player

        # Title
        self._text(player.name, 10, y, COL_TEXT_HIGHLIGHT, self.font_large)
        y += 28

        # HP
        hp_str = f"HP: {player.cur_hp}/{player.max_hp}"
        self._text(hp_str, 10, y, COL_HP_BAR)
        y += 20

        # HP bar
        bar_w = PANEL_W - 20
        bar_h = 8
        hp_pct = player.cur_hp / max(1, player.max_hp)
        pygame.draw.rect(self.screen, COL_HP_BAR_BG, (10, y, bar_w, bar_h))
        pygame.draw.rect(self.screen, COL_HP_BAR, (10, y, int(bar_w * hp_pct), bar_h))
        y += 16

        # Shields
        if player.shields > 0:
            self._text(f"Shields: {player.shields}", 10, y, COL_SHIELD)
            y += 20

        # SP
        self._text(f"SP: {game.sp}", 10, y, (255, 220, 100))
        y += 20

        # Level info
        self._text(f"Level: {game.level_num}/{game.MAX_LEVELS}", 10, y, COL_TEXT_DIM)
        y += 28

        # Spells (RW2 shows spell list with charges in left panel)
        self._text("-- Spells --", 10, y, COL_TEXT_DIM)
        y += 18
        for i, spell in enumerate(player.spells):
            if i == self.selected_spell_idx:
                color = COL_TEXT_HIGHLIGHT
                prefix = "> "
            else:
                color = COL_TEXT if spell.cur_charges > 0 else COL_TEXT_DIM
                prefix = "  "

            charges = f"{spell.cur_charges}/{spell.max_charges}" if spell.max_charges > 0 else ""
            cd = f" CD:{spell.cur_cool_down}" if spell.cur_cool_down > 0 else ""
            line = f"{prefix}{i+1}. {spell.name} [{charges}]{cd}"
            self._text(line, 6, y, color, self.font_small)
            y += 15
            if y > SCREEN_H - 60:
                break

        # Equipment (RW2 shows equipped items in left panel)
        if game.equipped:
            y += 10
            self._text("-- Equipment --", 10, y, COL_TEXT_DIM)
            y += 18
            for slot_name, equip in sorted(game.equipped.items()):
                self._text(f"  {slot_name}: {equip.name}", 6, y, (180, 180, 255), self.font_small)
                y += 15

        # Buffs (non-equipment)
        temp_buffs = [b for b in player.buffs if b.turns_left > 0]
        if temp_buffs:
            y += 10
            self._text("-- Buffs --", 10, y, COL_TEXT_DIM)
            y += 18
            for buff in temp_buffs[:6]:
                self._text(f"  {buff.name} ({buff.turns_left}t)", 6, y, buff.color, self.font_small)
                y += 15

    # -------------------------------------------------------------------
    # Right panel (Examine/Combat log — matches RW2's right panel)
    # -------------------------------------------------------------------
    def _draw_right_panel(self, game: Game) -> None:
        panel_x = SCREEN_W - PANEL_W
        panel = pygame.Rect(panel_x, 0, PANEL_W, SCREEN_H)
        pygame.draw.rect(self.screen, COL_PANEL_BG, panel)
        pygame.draw.line(self.screen, COL_PANEL_BORDER, (panel_x, 0), (panel_x, SCREEN_H))

        y = 10

        # Examine hovered tile (RW2 shows unit info when hovering)
        if self.hover_tile and game.current_level:
            tx, ty = self.hover_tile
            unit = game.current_level.get_unit_at(tx, ty)
            if unit and unit.is_alive():
                self._text(unit.name, panel_x + 10, y, COL_TEXT_HIGHLIGHT, self.font_large)
                y += 24
                self._text(f"HP: {unit.cur_hp}/{unit.max_hp}", panel_x + 10, y,
                           COL_ALLY_HP if unit.team == Team.PLAYER else COL_ENEMY_HP)
                y += 18

                # Resistances
                for tag in Tags.elements():
                    resist = unit.resists.get(tag, 0)
                    if resist != 0:
                        col = (100, 255, 100) if resist > 0 else (255, 100, 100)
                        self._text(f"  {tag.name}: {resist:+d}%", panel_x + 10, y, col, self.font_small)
                        y += 14

                # Spells
                if unit.spells:
                    y += 6
                    for sp in unit.spells[:4]:
                        self._text(f"  {sp.name} (d:{sp.damage})", panel_x + 10, y, COL_TEXT_DIM, self.font_small)
                        y += 14

                y += 10

        # Combat log (RW2 shows recent events in right panel)
        self._text("-- Combat Log --", panel_x + 10, max(y, SCREEN_H // 2), COL_TEXT_DIM)
        log_y = max(y + 18, SCREEN_H // 2 + 18)
        for line in self.combat_log[-20:]:
            self._text(line, panel_x + 6, log_y, COL_TEXT_DIM, self.font_small)
            log_y += 13
            if log_y > SCREEN_H - 10:
                break

    # -------------------------------------------------------------------
    # Status bar
    # -------------------------------------------------------------------
    def _draw_status_bar(self, game: Game) -> None:
        bar_h = 24
        bar_y = SCREEN_H - bar_h
        pygame.draw.rect(self.screen, COL_PANEL_BG, (PANEL_W, bar_y, SCREEN_W - 2 * PANEL_W, bar_h))

        if game.current_level:
            enemies = game.current_level.enemies_remaining()
            turn = game.current_level.turn_no
            text = f"Turn {turn}  |  Enemies: {enemies}  |  WASD/Arrows: move  |  1-9: select spell  |  Click: cast  |  Space: pass"
            self._text(text, PANEL_W + 10, bar_y + 4, COL_TEXT_DIM, self.font_small)

    # -------------------------------------------------------------------
    # Shop screen
    # -------------------------------------------------------------------
    def _draw_shop_screen(self, game: Game) -> None:
        y = 30

        title = f"Level {game.level_num} Complete!" if game.level_num > 0 else "Welcome, Wizard"
        self._text(title, SCREEN_W // 2 - 100, y, COL_TEXT_HIGHLIGHT, self.font_large)
        y += 40

        self._text(f"SP Available: {game.sp}", SCREEN_W // 2 - 60, y, (255, 220, 100), self.font_large)
        y += 40

        # Three columns: Elements | Shapes | Modifiers
        col_w = SCREEN_W // 3

        # Elements
        self._text("ELEMENTS (E)", 40, y, COL_TEXT_HIGHLIGHT)
        ey = y + 24
        from game.crafting.components import ELEMENTS, SHAPES, MODIFIERS
        for i, (name, elem) in enumerate(sorted(ELEMENTS.items())):
            owned = name in game.spell_library.owned_elements
            color = (100, 255, 100) if owned else COL_TEXT
            marker = "[*]" if owned else f"[{elem.sp_cost} SP]"
            self._text(f"  {name} {marker} (d:{elem.base_damage})", 20, ey, color, self.font_small)
            ey += 16

        # Shapes
        self._text("SHAPES (S)", col_w + 40, y, COL_TEXT_HIGHLIGHT)
        sy_pos = y + 24
        for name, shape in sorted(SHAPES.items()):
            owned = name in game.spell_library.owned_shapes
            color = (100, 255, 100) if owned else COL_TEXT
            marker = "[*]" if owned else f"[{shape.sp_cost} SP]"
            self._text(f"  {name} {marker} (r:{shape.base_range})", col_w + 20, sy_pos, color, self.font_small)
            sy_pos += 16

        # Modifiers
        self._text("MODIFIERS (M)", 2 * col_w + 40, y, COL_TEXT_HIGHLIGHT)
        my = y + 24
        for name, mod in sorted(MODIFIERS.items()):
            owned = name in game.spell_library.owned_modifiers
            color = (100, 255, 100) if owned else COL_TEXT
            marker = "[*]" if owned else f"[{mod.sp_cost} SP]"
            self._text(f"  {name} {marker}", 2 * col_w + 20, my, color, self.font_small)
            my += 16

        # Crafted spells
        craft_y = max(ey, sy_pos, my) + 30
        self._text("-- Your Spells --", SCREEN_W // 2 - 60, craft_y, COL_TEXT_HIGHLIGHT)
        craft_y += 24
        if game.spell_library.crafted_spells:
            for sp in game.spell_library.crafted_spells:
                self._text(f"  {sp.name}  (d:{sp.damage} r:{sp.range} c:{sp.max_charges})",
                           SCREEN_W // 2 - 120, craft_y, COL_TEXT, self.font_small)
                craft_y += 16
        else:
            self._text("  (none yet)", SCREEN_W // 2 - 40, craft_y, COL_TEXT_DIM)
            craft_y += 16

        # Instructions
        inst_y = SCREEN_H - 80
        self._text("Type element+shape to craft: e.g. 'fire bolt', 'ice burst empowered'", 40, inst_y, COL_TEXT_DIM, self.font_small)
        self._text("Press ENTER to start next level", 40, inst_y + 18, COL_TEXT_DIM, self.font_small)

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------
    def _text(self, text: str, x: int, y: int,
              color: tuple[int, int, int] = COL_TEXT,
              font: pygame.font.Font | None = None) -> None:
        if font is None:
            font = self.font
        surf = font.render(text, True, color)
        self.screen.blit(surf, (x, y))

    def _draw_help_overlay(self) -> None:
        """Draw keybinding help overlay (toggled with ?)."""
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))

        self._text("KEYBINDINGS", SCREEN_W // 2 - 60, 80, COL_TEXT_HIGHLIGHT, self.font_large)

        bindings = [
            ("Movement", ""),
            ("  WASD / Arrow Keys", "Move in 4 directions"),
            ("  Q E Z C", "Move diagonally"),
            ("  Space / Numpad 5", "Pass turn (skip)"),
            ("", ""),
            ("Spells", ""),
            ("  1-9", "Select spell"),
            ("  Left Click", "Cast selected spell at target"),
            ("  Tab", "Auto-target nearest enemy"),
            ("", ""),
            ("General", ""),
            ("  ? or H", "Toggle this help"),
            ("  F11", "Toggle fullscreen"),
            ("  Escape", "Cancel / Menu"),
            ("", ""),
            ("Shop", ""),
            ("  Click components", "Select element + shape + modifiers"),
            ("  Click CRAFT", "Create spell from selection"),
            ("  Enter", "Start next level"),
        ]

        y = 130
        for key, desc in bindings:
            if not key:
                y += 8
                continue
            self._text(key, 300, y, COL_TEXT_HIGHLIGHT if not key.startswith(" ") else COL_TEXT, self.font_small)
            if desc:
                self._text(desc, 580, y, COL_TEXT_DIM, self.font_small)
            y += 18

        self._text("Press ? or H to close", SCREEN_W // 2 - 80, SCREEN_H - 40, COL_TEXT_DIM, self.font_small)

    def add_log(self, message: str) -> None:
        self.combat_log.append(message)
        if len(self.combat_log) > 100:
            self.combat_log = self.combat_log[-50:]
