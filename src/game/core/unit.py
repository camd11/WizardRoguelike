"""Unit class — the entity that exists on the level grid.

Handles stat pipeline (tag_bonuses + global_bonuses), buff management,
spell list, equipment, and turn advancement.

Replicates RW2 Level.py:1514+ Unit class.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from game.constants import Tag, Tags, Team

if TYPE_CHECKING:
    from game.core.actions import CastAction, MoveAction, PassAction
    from game.core.buff import Buff
    from game.core.level import Level
    from game.core.spell_base import Spell


class Unit:
    """A player, enemy, or ally on the level grid."""

    def __init__(self) -> None:
        # Position
        self.x: int = 0
        self.y: int = 0

        # Identity
        self.name: str = "Unit"
        self.team: Team = Team.ENEMY
        self.tags: list[Tag] = [Tags.Living]
        self.asset_name: str = ""

        # Vitals
        self.max_hp: int = 10
        self.cur_hp: int = 10
        self.shields: int = 0

        # Movement
        self.flying: bool = False
        self.stationary: bool = False

        # Spells and items
        self.spells: list[Spell] = []
        self.buffs: list[Buff] = []

        # Resistances: {Tag: percentage} — positive = resist, negative = weakness
        self.resists: dict[Tag, int] = defaultdict(int)

        # Stat bonus accumulators (modified by buffs)
        # global_bonuses: apply to ALL spells (e.g., "damage" +3 for all spells)
        self.global_bonuses: dict[str, int] = defaultdict(int)
        self.global_bonuses_pct: dict[str, int] = defaultdict(int)
        # tag_bonuses: apply to spells with matching tag
        self.tag_bonuses: dict[Tag, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.tag_bonuses_pct: dict[Tag, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        # Back-reference
        self.level: Level | None = None

        # State flags
        self.killed: bool = False
        self.has_acted: bool = False
        self.turns_to_death: int = 0  # If > 0, temporary summon

        # Damage tracking (for cap)
        self._damage_instances_this_turn: int = 0

    def is_alive(self) -> bool:
        return self.cur_hp > 0 and not self.killed

    def is_player(self) -> bool:
        return self.team == Team.PLAYER

    def get_stat(self, base: int, spell: Spell, attr: str) -> int:
        """Apply all bonuses to a base stat value.

        Pipeline (matching RW2 Level.py:1650-1685):
            pct = global_pct + sum(tag_pct for matching tags)
            abs = global_abs + sum(tag_abs for matching tags)
            result = floor(base * (100 + pct) / 100) + abs
        """
        abs_bonus = self.global_bonuses.get(attr, 0)
        pct_bonus = self.global_bonuses_pct.get(attr, 0)

        for tag in spell.tags:
            abs_bonus += self.tag_bonuses.get(tag, {}).get(attr, 0)
            pct_bonus += self.tag_bonuses_pct.get(tag, {}).get(attr, 0)

        result = math.floor(base * (100 + pct_bonus) / 100) + abs_bonus
        return max(0, result)

    # -----------------------------------------------------------------------
    # Buff management
    # -----------------------------------------------------------------------
    def apply_buff(self, buff: Buff, duration: int = 0) -> bool:
        """Apply a buff to this unit. Returns True if applied successfully."""
        buff.turns_left = duration
        return buff.apply(self)

    def remove_buff(self, buff: Buff) -> None:
        """Remove a buff from this unit."""
        if buff in self.buffs:
            self.buffs.remove(buff)
            buff.unapply()

    def get_buff(self, buff_type: type) -> Buff | None:
        """Find the first buff of a given class."""
        for b in self.buffs:
            if type(b) is buff_type:
                return b
        return None

    def has_buff(self, buff_type: type) -> bool:
        return self.get_buff(buff_type) is not None

    def advance_buffs(self) -> None:
        """Tick all buffs. Called after unit's turn."""
        for buff in list(self.buffs):
            buff.advance()

    # -----------------------------------------------------------------------
    # Spell management
    # -----------------------------------------------------------------------
    def add_spell(self, spell: Spell) -> None:
        """Add a spell to this unit's spell list."""
        spell.caster = self
        self.spells.append(spell)

    def remove_spell(self, spell: Spell) -> None:
        if spell in self.spells:
            self.spells.remove(spell)
            spell.caster = None

    def pre_advance(self) -> None:
        """Called at start of turn: tick cooldowns, reset damage counter."""
        self._damage_instances_this_turn = 0
        self.has_acted = False
        for spell in self.spells:
            spell.pre_advance()

    # -----------------------------------------------------------------------
    # AI
    # -----------------------------------------------------------------------
    def get_ai_action(self) -> MoveAction | CastAction | PassAction | None:
        """AI decision making using the behavior system."""
        from game.ai.base_ai import get_ai_action as ai_decide
        return ai_decide(self)

    def _find_nearest_enemy(self) -> Unit | None:
        if self.level is None:
            return None
        best = None
        best_dist = float("inf")
        for unit in self.level.units:
            if unit.team == self.team or not unit.is_alive():
                continue
            dist = abs(unit.x - self.x) + abs(unit.y - self.y)
            if dist < best_dist:
                best_dist = dist
                best = unit
        return best

    # -----------------------------------------------------------------------
    # Death
    # -----------------------------------------------------------------------
    def kill(self, damage_event: Any = None) -> None:
        """Mark this unit as dead. Level handles removal and events."""
        self.killed = True
        self.cur_hp = 0

    def __repr__(self) -> str:
        return f"<{self.name} HP={self.cur_hp}/{self.max_hp} @({self.x},{self.y})>"
