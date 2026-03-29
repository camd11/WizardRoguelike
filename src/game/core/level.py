"""Level — the game grid with FOV, pathfinding, damage pipeline, and turn structure.

This is the most complex module, replicating RW2 Level.py:3104-4400.
"""
from __future__ import annotations

import math
from collections import deque
from typing import TYPE_CHECKING, Generator

import numpy as np
import tcod

from game.constants import (
    DAMAGE_INSTANCE_CAP,
    LEVEL_SIZE,
    MAX_RESIST,
    Tag,
    Team,
    TileType,
)
from game.core.events import (
    EventHandler,
    EventOnBuffApply,
    EventOnBuffRemove,
    EventOnDamaged,
    EventOnDeath,
    EventOnHealed,
    EventOnMoved,
    EventOnPass,
    EventOnPreDamaged,
    EventOnSpellCast,
    EventOnTurnEnd,
    EventOnUnitAdded,
)
from game.core.tile import Tile
from game.core.types import DamageEvent, Point

if TYPE_CHECKING:
    from game.core.actions import CastAction, MoveAction, PassAction
    from game.core.spell_base import Spell
    from game.core.unit import Unit


class Level:
    """The game grid — owns tiles, units, and the turn loop."""

    def __init__(self, width: int = LEVEL_SIZE, height: int = LEVEL_SIZE) -> None:
        self.width = width
        self.height = height

        # 2D tile array [x][y]
        self.tiles: list[list[Tile]] = [
            [Tile(x, y) for y in range(height)]
            for x in range(width)
        ]

        # Unit list
        self.units: list[Unit] = []

        # Event system
        self.event_handler = EventHandler()

        # Spell animation queue (generators from spell.cast())
        self.active_spells: deque[tuple[Generator, Unit | None]] = deque()

        # Turn tracking
        self.turn_no: int = 0
        self.is_awaiting_input: bool = False
        self._requested_action: MoveAction | CastAction | PassAction | None = None

        # FOV/pathfinding arrays (rebuilt on tile changes)
        self._transparency: np.ndarray = np.ones((width, height), dtype=np.bool_)
        self._walkable: np.ndarray = np.ones((width, height), dtype=np.bool_)
        self._rebuild_arrays()

    # -----------------------------------------------------------------------
    # Tile access
    # -----------------------------------------------------------------------
    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def get_tile(self, x: int, y: int) -> Tile | None:
        if self.in_bounds(x, y):
            return self.tiles[x][y]
        return None

    def set_tile_type(self, x: int, y: int, tile_type: TileType) -> None:
        if self.in_bounds(x, y):
            self.tiles[x][y].tile_type = tile_type
            self._update_arrays(x, y)

    # -----------------------------------------------------------------------
    # Unit management
    # -----------------------------------------------------------------------
    def add_unit(self, unit: Unit, x: int, y: int) -> bool:
        """Place a unit on the grid. Returns False if tile is occupied."""
        if not self.in_bounds(x, y):
            return False
        tile = self.tiles[x][y]
        if tile.unit is not None or tile.is_wall:
            return False

        unit.x = x
        unit.y = y
        unit.level = self
        tile.unit = unit
        self.units.append(unit)

        # Subscribe any existing buff events
        for buff in unit.buffs:
            buff._subscribe_events(self.event_handler)

        self.event_handler.raise_event(EventOnUnitAdded(unit=unit), entity=unit)
        return True

    def remove_unit(self, unit: Unit) -> None:
        """Remove a unit from the grid."""
        if self.in_bounds(unit.x, unit.y):
            tile = self.tiles[unit.x][unit.y]
            if tile.unit is unit:
                tile.unit = None

        # Unsubscribe buff events
        for buff in list(unit.buffs):
            buff._unsubscribe_events(self.event_handler)

        if unit in self.units:
            self.units.remove(unit)
        unit.level = None

    def get_unit_at(self, x: int, y: int) -> Unit | None:
        if self.in_bounds(x, y):
            return self.tiles[x][y].unit
        return None

    def get_units_in_ball(self, origin: Point, radius: float) -> list[Unit]:
        """Get all units within Euclidean radius of origin."""
        result = []
        for unit in self.units:
            if unit.is_alive():
                dist = math.sqrt((unit.x - origin.x)**2 + (unit.y - origin.y)**2)
                if dist <= radius + 0.5:
                    result.append(unit)
        return result

    # -----------------------------------------------------------------------
    # Movement
    # -----------------------------------------------------------------------
    def act_move(self, unit: Unit, x: int, y: int) -> bool:
        """Move a unit to an adjacent tile. Returns True on success."""
        if not self.in_bounds(x, y):
            return False

        tile = self.tiles[x][y]
        if not tile.can_walk(unit.flying):
            return False

        # Chebyshev distance must be 1
        if max(abs(x - unit.x), abs(y - unit.y)) != 1:
            return False

        # Clear old tile
        old_tile = self.tiles[unit.x][unit.y]
        if old_tile.unit is unit:
            old_tile.unit = None

        # Place on new tile
        unit.x = x
        unit.y = y
        tile.unit = unit

        self.event_handler.raise_event(
            EventOnMoved(unit=unit, x=x, y=y, teleport=False), entity=unit
        )
        return True

    def teleport(self, unit: Unit, x: int, y: int) -> bool:
        """Move unit to any tile (ignores adjacency)."""
        if not self.in_bounds(x, y):
            return False
        tile = self.tiles[x][y]
        if tile.unit is not None or tile.is_wall:
            return False

        old_tile = self.tiles[unit.x][unit.y]
        if old_tile.unit is unit:
            old_tile.unit = None

        unit.x = x
        unit.y = y
        tile.unit = unit

        self.event_handler.raise_event(
            EventOnMoved(unit=unit, x=x, y=y, teleport=True), entity=unit
        )
        return True

    # -----------------------------------------------------------------------
    # Spell casting
    # -----------------------------------------------------------------------
    def act_cast(self, unit: Unit, spell: Spell, x: int, y: int,
                 pay_costs: bool = True) -> bool:
        """Cast a spell. Queues the generator for frame-by-frame animation."""
        if pay_costs:
            if not spell.can_cast(x, y) or not spell.can_pay_costs():
                return False
            spell.pay_costs()

        gen = spell.cast(x, y)
        self.active_spells.append((gen, unit))

        self.event_handler.raise_event(
            EventOnSpellCast(spell=spell, caster=unit, x=x, y=y, pay_costs=pay_costs),
            entity=unit,
        )
        return True

    def queue_spell(self, gen: Generator, caster: Unit | None = None) -> None:
        """Queue a spell generator (e.g., from a buff trigger)."""
        self.active_spells.append((gen, caster))

    def advance_spells(self) -> bool:
        """Advance all queued spell generators by one frame.

        Returns True if any spells are still active.
        """
        finished = []
        for i, (gen, caster) in enumerate(self.active_spells):
            try:
                next(gen)
            except StopIteration:
                finished.append(i)

        # Remove finished generators by index (reverse to preserve indices)
        for i in reversed(finished):
            del self.active_spells[i]

        return len(self.active_spells) > 0

    # -----------------------------------------------------------------------
    # Damage pipeline (replicates RW2 Level.py:4137-4290)
    # -----------------------------------------------------------------------
    def deal_damage(self, x: int, y: int, amount: int, damage_type: Tag,
                    source: object) -> int:
        """Deal damage at a tile. Returns actual damage dealt.

        Pipeline:
        1. Find unit at tile
        2. Check damage instance cap
        3. Apply resistance
        4. Raise EventOnPreDamaged
        5. Shield check
        6. Cap to current HP / missing HP
        7. Apply damage
        8. Raise EventOnDamaged or EventOnHealed
        9. Kill check
        """
        unit = self.get_unit_at(x, y)
        if unit is None or not unit.is_alive():
            # Check for damageable props (lairs)
            if self.in_bounds(x, y):
                tile = self.tiles[x][y]
                if tile.prop and hasattr(tile.prop, 'take_damage'):
                    return tile.prop.take_damage(amount)
            return 0

        # Damage instance cap
        if unit._damage_instances_this_turn >= DAMAGE_INSTANCE_CAP:
            return 0
        unit._damage_instances_this_turn += 1

        original_amount = amount

        # Apply resistance (check source for pierce effects)
        resist = min(unit.resists.get(damage_type, 0), MAX_RESIST)

        # Piercing: source spell can reduce effective resistance
        pierce_pct = 0
        if hasattr(source, 'get_pierce_pct'):
            pierce_pct = source.get_pierce_pct()
        if pierce_pct > 0 and resist > 0:
            resist = max(0, int(resist * (100 - pierce_pct) / 100))

        amount = math.ceil(amount * (100 - resist) / 100)

        # Pre-damage event (allows modification/interception)
        self.event_handler.raise_event(
            EventOnPreDamaged(
                unit=unit, damage=amount, original_damage=original_amount,
                damage_type=damage_type, source=source,
            ),
            entity=unit,
        )

        # Shield check
        if amount > 0 and unit.shields > 0:
            unit.shields -= 1
            return 0

        # Healing case (negative resistance = extra damage, but also handle healing spells)
        if amount < 0:
            # This is healing
            heal = min(-amount, unit.max_hp - unit.cur_hp)
            if heal > 0:
                unit.cur_hp += heal
                self.event_handler.raise_event(
                    EventOnHealed(unit=unit, heal=heal, source=source),
                    entity=unit,
                )
            return -heal

        # Cap damage to current HP
        amount = min(amount, unit.cur_hp)

        if amount <= 0:
            return 0

        # Apply damage
        unit.cur_hp -= amount

        damage_event = DamageEvent(
            unit=unit, damage=amount, damage_type=damage_type, source=source
        )

        self.event_handler.raise_event(
            EventOnDamaged(unit=unit, damage=amount, damage_type=damage_type, source=source),
            entity=unit,
        )

        # Kill check
        if unit.cur_hp <= 0:
            unit.kill(damage_event)
            self.event_handler.raise_event(
                EventOnDeath(unit=unit, damage_event=damage_event),
                entity=unit,
            )
            self._cleanup_dead_unit(unit)

        return amount

    def deal_damage_point(self, point: Point, amount: int, damage_type: Tag,
                          source: object) -> int:
        """Convenience wrapper for deal_damage with a Point."""
        return self.deal_damage(point.x, point.y, amount, damage_type, source)

    def _cleanup_dead_unit(self, unit: Unit) -> None:
        """Remove a dead unit from the grid (but keep in units list until turn end)."""
        if self.in_bounds(unit.x, unit.y):
            tile = self.tiles[unit.x][unit.y]
            if tile.unit is unit:
                tile.unit = None

    # -----------------------------------------------------------------------
    # Turn structure (replicates RW2 Level.py:3582-3664)
    # -----------------------------------------------------------------------
    def iter_frame(self) -> Generator[bool, MoveAction | CastAction | PassAction | None, None]:
        """Main game loop generator. Yields True at end of each turn.

        The caller sends player actions via .send() when is_awaiting_input is True.
        """
        while True:
            # Drain spell animations
            while self.advance_spells():
                yield False

            self.turn_no += 1

            # Reset per-turn state
            for unit in self.units:
                unit._damage_instances_this_turn = 0

            # Cache unit list at turn start (new summons don't act this turn)
            turn_units = list(self.units)

            # Two-phase: player phase, then enemy phase
            for is_player_phase in (True, False):
                phase_units = [
                    u for u in turn_units
                    if u.is_alive() and u.is_player() == is_player_phase
                ]

                for unit in phase_units:
                    if not unit.is_alive():
                        continue

                    unit.pre_advance()

                    # Check for stun/freeze — skip turn if incapacitated
                    is_stunned = any(
                        b.name in ("Stunned", "Frozen")
                        for b in unit.buffs
                    )

                    if is_stunned:
                        pass  # Skip action, just advance buffs below
                    elif unit.is_player():
                        # Wait for player input
                        self.is_awaiting_input = True
                        action = yield False
                        self.is_awaiting_input = False

                        if action is not None:
                            self._execute_action(unit, action)
                    else:
                        # AI turn
                        action = unit.get_ai_action()
                        if action is not None:
                            self._execute_action(unit, action)

                    # Drain spell animations after each unit
                    while self.advance_spells():
                        yield False

                    # Advance buffs after unit acts
                    unit.advance_buffs()

                    # Drain animations from buff effects
                    while self.advance_spells():
                        yield False

            # Advance props (lairs) and clouds
            for x in range(self.width):
                for y in range(self.height):
                    tile = self.tiles[x][y]
                    # Advance props
                    if tile.prop and hasattr(tile.prop, 'advance'):
                        tile.prop.advance(self)
                    # Advance clouds (remove expired ones)
                    if tile.cloud and hasattr(tile.cloud, 'advance'):
                        alive = tile.cloud.advance(self)
                        if not alive:
                            tile.cloud = None

            # Clean up dead units
            self.units = [u for u in self.units if u.is_alive()]

            # Tick temporary summons
            for unit in list(self.units):
                if unit.turns_to_death > 0:
                    unit.turns_to_death -= 1
                    if unit.turns_to_death <= 0:
                        unit.kill()
                        self._cleanup_dead_unit(unit)

            self.units = [u for u in self.units if u.is_alive()]

            self.event_handler.raise_event(EventOnTurnEnd(turn_no=self.turn_no))

            yield True  # Turn complete

    def _execute_action(self, unit: Unit, action: object) -> None:
        """Execute a player or AI action."""
        from game.core.actions import CastAction, MoveAction, PassAction

        if isinstance(action, MoveAction):
            self.act_move(unit, action.x, action.y)
        elif isinstance(action, CastAction):
            self.act_cast(unit, action.spell, action.x, action.y)
        elif isinstance(action, PassAction):
            self.event_handler.raise_event(EventOnPass(unit=unit), entity=unit)

    # -----------------------------------------------------------------------
    # FOV / LOS
    # -----------------------------------------------------------------------
    def has_los(self, start: Point, end: Point) -> bool:
        """Check line of sight between two points using Bresenham's line."""
        from game.core.shapes import get_line

        for p in get_line(start, end)[1:-1]:  # Exclude endpoints
            if not self.in_bounds(p.x, p.y):
                return False
            if self.tiles[p.x][p.y].blocks_los():
                return False
        return True

    def compute_fov(self, x: int, y: int, radius: int = 0) -> np.ndarray:
        """Compute field of view from a position. Returns bool array [width, height]."""
        if radius == 0:
            radius = max(self.width, self.height)
        return tcod.map.compute_fov(
            self._transparency.T,  # tcod expects [y, x]
            pov=(y, x),
            radius=radius,
            algorithm=tcod.constants.FOV_SYMMETRIC_SHADOWCAST,
        ).T  # Back to [x, y]

    # -----------------------------------------------------------------------
    # Pathfinding
    # -----------------------------------------------------------------------
    def find_path(self, x0: int, y0: int, x1: int, y1: int,
                  flying: bool = False) -> list[tuple[int, int]]:
        """A* pathfinding. Returns list of (x, y) from start to end inclusive."""
        cost = np.ones((self.width, self.height), dtype=np.int32)

        for x in range(self.width):
            for y in range(self.height):
                tile = self.tiles[x][y]
                if tile.is_wall:
                    cost[x][y] = 0
                elif tile.is_chasm and not flying:
                    cost[x][y] = 0
                elif tile.unit is not None:
                    cost[x][y] = 5  # Prefer paths around units

        # tcod uses [y, x] ordering
        graph = tcod.path.AStar(cost.T)
        path_yx = graph.get_path(y0, x0, y1, x1)

        result = [(x0, y0)]
        for py, px in path_yx:
            result.append((px, py))

        return result

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------
    def _rebuild_arrays(self) -> None:
        """Rebuild transparency and walkable arrays from tiles."""
        for x in range(self.width):
            for y in range(self.height):
                tile = self.tiles[x][y]
                self._transparency[x][y] = not tile.blocks_los()
                self._walkable[x][y] = tile.tile_type != TileType.WALL

    def _update_arrays(self, x: int, y: int) -> None:
        tile = self.tiles[x][y]
        self._transparency[x][y] = not tile.blocks_los()
        self._walkable[x][y] = tile.tile_type != TileType.WALL

    # -----------------------------------------------------------------------
    # Queries
    # -----------------------------------------------------------------------
    def get_player(self) -> Unit | None:
        for unit in self.units:
            if unit.is_player():
                return unit
        return None

    def enemies_remaining(self) -> int:
        return sum(1 for u in self.units if u.team == Team.ENEMY and u.is_alive())

    def lairs_remaining(self) -> int:
        """Count active (non-destroyed) lairs."""
        from game.core.prop import Lair
        count = 0
        for x in range(self.width):
            for y in range(self.height):
                tile = self.tiles[x][y]
                if isinstance(tile.prop, Lair) and not tile.prop.destroyed:
                    count += 1
        return count

    def is_clear(self) -> bool:
        """Level is clear when all enemies AND all lairs are destroyed."""
        return self.enemies_remaining() == 0 and self.lairs_remaining() == 0
