"""Base Spell class with generator-based cast() and stat pipeline.

Replicates RW2 Level.py:392-813.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Generator

from game.constants import Tag
from game.core.types import Point

if TYPE_CHECKING:
    from game.core.level import Level
    from game.core.unit import Unit


class Spell:
    """Base class for all spells (both crafted and monster abilities).

    Key pattern: cast(x, y) returns a generator that yields between animation
    frames. The Level's active_spells deque drives this generator.
    """

    def __init__(self) -> None:
        self.name: str = "Spell"
        self.description: str = ""

        # Stats
        self.damage: int = 0
        self.damage_type: Tag | None = None
        self.range: int = 0
        self.radius: int = 0
        self.duration: int = 0
        self.max_charges: int = 0
        self.cur_charges: int = 0
        self.cool_down: int = 0
        self.cur_cool_down: int = 0
        self.hp_cost: int = 0

        # Targeting
        self.melee: bool = False
        self.can_target_self: bool = False
        self.can_target_empty: bool = True
        self.must_target_empty: bool = False
        self.requires_los: bool = True

        # Tags (element + school + shape pseudo-tags)
        self.tags: list[Tag] = []

        # Owner reference (set when spell is added to a unit)
        self.caster: Unit | None = None

        self.on_init()

    def on_init(self) -> None:
        """Override to configure spell stats. Called from __init__."""
        pass

    @property
    def level(self) -> Level | None:
        """The level the caster is in."""
        return self.caster.level if self.caster else None

    def get_stat(self, attr: str, base: int | None = None) -> int:
        """Get a stat value with all bonuses applied.

        Pipeline: base * (100 + pct_bonuses) / 100 + abs_bonuses
        Bonuses come from: global, tag-based, spell-specific on the caster.
        """
        if base is None:
            base = getattr(self, attr, 0)

        if self.caster is None:
            return base

        return self.caster.get_stat(base, self, attr)

    def can_cast(self, x: int, y: int) -> bool:
        """Check if this spell can be cast at the target location."""
        if self.caster is None or self.level is None:
            return False

        caster_pos = Point(self.caster.x, self.caster.y)
        target_pos = Point(x, y)

        # Range check
        effective_range = self.get_stat("range")
        if self.melee:
            if caster_pos.chebyshev(target_pos) > 1:
                return False
        elif caster_pos.distance_to(target_pos) > effective_range + 0.5:
            return False

        # LOS check
        if self.requires_los and not self.level.has_los(caster_pos, target_pos):
            return False

        # Target validation
        if not self.level.in_bounds(x, y):
            return False

        unit_at_target = self.level.get_unit_at(x, y)
        if unit_at_target is None and not self.can_target_empty:
            return False
        if unit_at_target is not None and self.must_target_empty:
            return False
        if unit_at_target is self.caster and not self.can_target_self:
            return False

        return True

    def can_pay_costs(self) -> bool:
        """Check if caster can afford this spell."""
        if self.caster is None:
            return False
        if self.max_charges > 0 and self.cur_charges <= 0:
            return False
        if self.cur_cool_down > 0:
            return False
        if self.hp_cost > 0 and self.caster.cur_hp <= self.hp_cost:
            return False
        return True

    def pay_costs(self) -> None:
        """Deduct spell costs from caster."""
        if self.max_charges > 0:
            self.cur_charges -= 1
        if self.cool_down > 0:
            self.cur_cool_down = self.cool_down
        if self.hp_cost > 0 and self.caster is not None:
            self.caster.cur_hp -= self.hp_cost

    def pre_advance(self) -> None:
        """Called at start of caster's turn. Ticks cooldown."""
        if self.cur_cool_down > 0:
            self.cur_cool_down -= 1

    def cast(self, x: int, y: int) -> Generator[None, None, None]:
        """Override: generator that executes the spell, yielding between frames."""
        self.cast_instant(x, y)
        yield

    def cast_instant(self, x: int, y: int) -> None:
        """Override: non-animated fallback for simple spells."""
        pass

    def get_impacted_tiles(self, x: int, y: int) -> list[Point]:
        """Override: return tiles that would be affected (for UI targeting preview)."""
        return [Point(x, y)]

    def get_ai_target(self) -> Point | None:
        """Default AI targeting: nearest enemy in range."""
        if self.caster is None or self.level is None:
            return None

        caster_pos = Point(self.caster.x, self.caster.y)
        best_target = None
        best_dist = float("inf")

        for unit in self.level.units:
            if unit.team == self.caster.team:
                continue
            if not unit.is_alive():
                continue
            pos = Point(unit.x, unit.y)
            dist = caster_pos.distance_to(pos)
            if dist < best_dist and self.can_cast(unit.x, unit.y):
                best_dist = dist
                best_target = pos

        return best_target

    def __repr__(self) -> str:
        return f"<{self.name} (d={self.damage} r={self.range})>"
