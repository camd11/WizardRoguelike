"""Visual effects system: damage numbers, tile flashes, projectile trails, bursts."""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class DamageNumber:
    """Floating damage number that drifts upward and fades."""
    x: int
    y: int
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


@dataclass
class ProjectileTrail:
    """A fading trail left by bolt/beam projectiles."""
    x: int
    y: int
    color: tuple[int, int, int]
    created: float = field(default_factory=time.time)
    duration: float = 0.3

    @property
    def alive(self) -> bool:
        return time.time() - self.created < self.duration

    @property
    def alpha(self) -> int:
        elapsed = time.time() - self.created
        return max(0, int(120 * (1 - elapsed / self.duration)))


@dataclass
class BurstRing:
    """An expanding ring effect for burst/explosion spells."""
    x: int
    y: int
    radius: int  # Current ring number
    color: tuple[int, int, int]
    created: float = field(default_factory=time.time)
    duration: float = 0.15

    @property
    def alive(self) -> bool:
        return time.time() - self.created < self.duration

    @property
    def alpha(self) -> int:
        elapsed = time.time() - self.created
        return max(0, int(150 * (1 - elapsed / self.duration)))


@dataclass
class DeathEffect:
    """Skull/fade effect when a unit dies."""
    x: int
    y: int
    created: float = field(default_factory=time.time)
    duration: float = 0.5

    @property
    def alive(self) -> bool:
        return time.time() - self.created < self.duration

    @property
    def alpha(self) -> int:
        elapsed = time.time() - self.created
        return max(0, int(200 * (1 - elapsed / self.duration)))

    @property
    def scale(self) -> float:
        elapsed = time.time() - self.created
        return 1.0 + elapsed / self.duration * 0.5


class AnimationManager:
    """Tracks all active visual effects."""

    def __init__(self) -> None:
        self.damage_numbers: list[DamageNumber] = []
        self.tile_flashes: list[TileFlash] = []
        self.projectile_trails: list[ProjectileTrail] = []
        self.burst_rings: list[BurstRing] = []
        self.death_effects: list[DeathEffect] = []

    def add_damage_number(self, x: int, y: int, amount: int,
                          color: tuple[int, int, int] = (255, 60, 60)) -> None:
        self.damage_numbers.append(DamageNumber(x, y, amount, color))

    def add_tile_flash(self, x: int, y: int,
                       color: tuple[int, int, int] = (255, 200, 50)) -> None:
        self.tile_flashes.append(TileFlash(x, y, color))

    def add_projectile_trail(self, x: int, y: int,
                             color: tuple[int, int, int] = (255, 200, 80)) -> None:
        self.projectile_trails.append(ProjectileTrail(x, y, color))

    def add_burst_ring(self, x: int, y: int, radius: int,
                       color: tuple[int, int, int] = (255, 150, 50)) -> None:
        self.burst_rings.append(BurstRing(x, y, radius, color))

    def add_death_effect(self, x: int, y: int) -> None:
        self.death_effects.append(DeathEffect(x, y))

    def update(self) -> None:
        """Remove expired effects."""
        self.damage_numbers = [d for d in self.damage_numbers if d.alive]
        self.tile_flashes = [f for f in self.tile_flashes if f.alive]
        self.projectile_trails = [p for p in self.projectile_trails if p.alive]
        self.burst_rings = [b for b in self.burst_rings if b.alive]
        self.death_effects = [d for d in self.death_effects if d.alive]
