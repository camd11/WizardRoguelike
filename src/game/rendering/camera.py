"""Camera / viewport management for scrolling the level view."""
from __future__ import annotations

from game.rendering.asset_loader import DISPLAY_TILE


class Camera:
    """Manages the viewport offset so the player stays centered."""

    def __init__(self, screen_w: int, screen_h: int,
                 panel_left: int = 220, panel_right: int = 220) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.panel_left = panel_left
        self.panel_right = panel_right

        # Viewport area (between panels)
        self.view_w = screen_w - panel_left - panel_right
        self.view_h = screen_h

        # Camera offset in pixels
        self.offset_x: int = 0
        self.offset_y: int = 0

    def center_on(self, tile_x: int, tile_y: int) -> None:
        """Center the viewport on a tile position."""
        px = tile_x * DISPLAY_TILE + DISPLAY_TILE // 2
        py = tile_y * DISPLAY_TILE + DISPLAY_TILE // 2
        self.offset_x = px - self.view_w // 2
        self.offset_y = py - self.view_h // 2

    def tile_to_screen(self, tile_x: int, tile_y: int) -> tuple[int, int]:
        """Convert tile coordinates to screen pixel coordinates."""
        sx = tile_x * DISPLAY_TILE - self.offset_x + self.panel_left
        sy = tile_y * DISPLAY_TILE - self.offset_y
        return sx, sy

    def screen_to_tile(self, screen_x: int, screen_y: int) -> tuple[int, int]:
        """Convert screen pixel coordinates to tile coordinates."""
        tx = (screen_x - self.panel_left + self.offset_x) // DISPLAY_TILE
        ty = (screen_y + self.offset_y) // DISPLAY_TILE
        return tx, ty

    def is_visible(self, tile_x: int, tile_y: int) -> bool:
        """Check if a tile is within the current viewport."""
        sx, sy = self.tile_to_screen(tile_x, tile_y)
        return (self.panel_left - DISPLAY_TILE <= sx <= self.panel_left + self.view_w and
                -DISPLAY_TILE <= sy <= self.view_h)
