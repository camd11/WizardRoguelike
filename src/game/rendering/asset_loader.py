"""Asset loader — loads and caches RW2 PNG sprites from the symlinked rl_data/."""
from __future__ import annotations

import os
from pathlib import Path

import pygame

# Resolve asset root relative to this file → ../../assets/rl_data
_ASSET_ROOT = Path(__file__).resolve().parents[2] / "assets" / "rl_data"
# Fallback for installed package
if not _ASSET_ROOT.exists():
    _ASSET_ROOT = Path(__file__).resolve().parents[3] / "assets" / "rl_data"

TILE_SIZE = 16  # RW2 native sprite size
DISPLAY_TILE = 32  # We render at 2x for readability


class AssetLoader:
    """Loads and caches sprites. Falls back to colored rectangles if asset missing."""

    def __init__(self) -> None:
        self._cache: dict[str, pygame.Surface] = {}
        self._missing: set[str] = set()

    def get_sprite(self, path: str, color_fallback: tuple[int, int, int] = (200, 0, 200)) -> pygame.Surface:
        """Load a sprite by relative path (no extension). Returns DISPLAY_TILE×DISPLAY_TILE surface."""
        if path in self._cache:
            return self._cache[path]

        full = _ASSET_ROOT / (path + ".png")
        if full.exists():
            try:
                raw = pygame.image.load(str(full)).convert_alpha()
                # Take the first TILE_SIZE×TILE_SIZE frame (sprite sheets have multiple frames)
                frame = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                frame.blit(raw, (0, 0), (0, 0, TILE_SIZE, TILE_SIZE))
                scaled = pygame.transform.scale(frame, (DISPLAY_TILE, DISPLAY_TILE))
                self._cache[path] = scaled
                return scaled
            except Exception:
                pass

        # Fallback: colored square
        if path not in self._missing:
            self._missing.add(path)
        surf = pygame.Surface((DISPLAY_TILE, DISPLAY_TILE))
        surf.fill(color_fallback)
        self._cache[path] = surf
        return surf

    def get_unit_sprite(self, asset_name: str) -> pygame.Surface:
        """Load a unit/character sprite."""
        if not asset_name:
            return self.get_sprite("_placeholder_unit", (0, 180, 0))
        return self.get_sprite(asset_name, (0, 180, 0))

    def get_floor_sprite(self, biome_floor: str) -> pygame.Surface:
        return self.get_sprite(biome_floor, (60, 60, 60))

    def get_wall_sprite(self, biome_wall: str) -> pygame.Surface:
        return self.get_sprite(biome_wall, (100, 100, 100))

    def get_effect_sprite(self, name: str) -> pygame.Surface:
        return self.get_sprite(f"tiles/effects/{name}", (255, 255, 0))
