"""Simple animation / visual effects system."""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class DamageNumber:
    """Floating damage number that drifts upward and fades."""
    x: int  # tile x
    y: int  # tile y
    amount: int
    color: tuple[int, int, int]
    created: float = field(default_factory=time.time)
    duration: float = 0.8

    @property
    def alive(self) -> bool:
        return time.time() - self.created < self.duration

    @property
    def alpha(self) -> int:
        elapsed = time.time() - self.created
        return max(0, int(255 * (1 - elapsed / self.duration)))

    @property
    def y_offset(self) -> int:
        elapsed = time.time() - self.created
        return int(-20 * elapsed / self.duration)


@dataclass
class TileFlash:
    """Brief color flash on a tile (for spell impacts)."""
    x: int
    y: int
    color: tuple[int, int, int]
    created: float = field(default_factory=time.time)
    duration: float = 0.2

    @property
    def alive(self) -> bool:
        return time.time() - self.created < self.duration

    @property
    def alpha(self) -> int:
        elapsed = time.time() - self.created
        return max(0, int(180 * (1 - elapsed / self.duration)))


class AnimationManager:
    """Tracks active visual effects."""

    def __init__(self) -> None:
        self.damage_numbers: list[DamageNumber] = []
        self.tile_flashes: list[TileFlash] = []

    def add_damage_number(self, x: int, y: int, amount: int,
                          color: tuple[int, int, int] = (255, 60, 60)) -> None:
        self.damage_numbers.append(DamageNumber(x, y, amount, color))

    def add_tile_flash(self, x: int, y: int,
                       color: tuple[int, int, int] = (255, 200, 50)) -> None:
        self.tile_flashes.append(TileFlash(x, y, color))

    def update(self) -> None:
        """Remove expired effects."""
        self.damage_numbers = [d for d in self.damage_numbers if d.alive]
        self.tile_flashes = [f for f in self.tile_flashes if f.alive]
