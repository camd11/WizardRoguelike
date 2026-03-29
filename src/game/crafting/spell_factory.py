"""CraftedSpell — runtime composition of Element + Shape + Modifiers.

This is the core differentiator: instead of 200+ hardcoded spell classes,
spells are assembled from components at runtime.
"""
from __future__ import annotations

import math
from typing import Generator

from game.constants import Tags
from game.content.elements import get_element_handler
from game.content.modifiers import get_modifier_handler
from game.content.shapes import get_shape_handler
from game.crafting.components import Element, Modifier, Shape
from game.crafting.recipe_validator import validate_recipe
from game.core.spell_base import Spell
from game.core.types import Point


class CraftedSpell(Spell):
    """A spell composed from an Element, Shape, and 0-2 Modifiers.

    Stats are computed from component data + caster bonuses.
    cast() delegates to the shape handler, which calls back into
    _apply_element_secondary() and _apply_modifier_effects() at each hit point.
    """

    def __init__(self, element: Element, shape: Shape,
                 modifiers: list[Modifier] | None = None) -> None:
        self._element = element
        self._shape = shape
        self._modifiers = modifiers or []

        # Validate before construction
        result = validate_recipe(element, shape, self._modifiers)
        if not result.valid:
            raise ValueError(f"Invalid recipe: {result.errors}")

        # Get handler modules
        self._element_handler = get_element_handler(element.name)
        self._shape_handler = get_shape_handler(shape.name)
        self._modifier_handlers = [
            get_modifier_handler(m.name) for m in self._modifiers
        ]

        super().__init__()

    def on_init(self) -> None:
        """Compute spell stats from components."""
        # Name generation
        mod_prefix = " ".join(m.name for m in self._modifiers)
        if mod_prefix:
            self.name = f"{mod_prefix} {self._element.name} {self._shape.name}"
        else:
            self.name = f"{self._element.name} {self._shape.name}"

        # Base stats from components
        self.damage = self._element.base_damage
        self.damage_type = self._element.tag
        self.range = self._shape.base_range
        self.radius = self._shape.base_radius
        self.max_charges = self._shape.base_charges
        self.cur_charges = self._shape.base_charges
        self.melee = self._shape.melee
        self.requires_los = self._shape.requires_los
        self.can_target_self = self._shape.can_target_self
        self.can_target_empty = self._shape.can_target_empty

        # Store element DOT params for handler access
        self._element_dot_damage = self._element.dot_damage
        self._element_dot_duration = self._element.dot_duration

        # Tags: element tag + Sorcery + shape pseudo-tag
        self.tags = [self._element.tag, Tags.Sorcery, self._shape.tag]

        # Apply modifier stat changes
        self._apply_modifier_stats()

        # Generate description
        self.description = self._build_description()

    def _apply_modifier_stats(self) -> None:
        """Apply modifier stat modifications."""
        for mod in self._modifiers:
            # Damage multiplier
            if mod.damage_mult != 1.0:
                self.damage = int(self.damage * mod.damage_mult)

            # Range bonus
            self.range += mod.range_bonus

            # Radius bonus
            self.radius += mod.radius_bonus

            # Charges bonus
            self.max_charges += mod.charges_bonus
            self.cur_charges += mod.charges_bonus

            # Duration (channeled)
            if mod.channel_turns > 0:
                self.duration = mod.channel_turns

    def _build_description(self) -> str:
        parts = [f"{self._element.description}"]
        parts.append(f"Shape: {self._shape.description}")
        for mod in self._modifiers:
            parts.append(f"{mod.name}: {mod.description}")
        parts.append(f"Damage: {self.damage} | Range: {self.range} | Charges: {self.max_charges}")
        if self.radius > 0:
            parts.append(f"Radius: {self.radius}")
        return "\n".join(parts)

    # -------------------------------------------------------------------
    # Cast — delegates to shape handler
    # -------------------------------------------------------------------
    def cast(self, x: int, y: int) -> Generator[None, None, None]:
        """Cast the spell by delegating to the shape handler's cast()."""
        # Homing retargeting
        actual_x, actual_y = x, y
        for mod, handler in zip(self._modifiers, self._modifier_handlers):
            if mod.homing and hasattr(handler, 'retarget'):
                new_target = handler.retarget(self, x, y)
                actual_x, actual_y = new_target.x, new_target.y

        # Channeled: cast once then apply channel buff
        has_channel = any(m.channel_turns > 0 for m in self._modifiers)
        if has_channel:
            # First cast
            yield from self._shape_cast(actual_x, actual_y)
            # Apply channel buff for subsequent turns
            from game.content.modifiers.channeled import ChannelBuff
            for mod in self._modifiers:
                if mod.channel_turns > 0:
                    channel = ChannelBuff(self, actual_x, actual_y, mod.channel_turns)
                    self.caster.apply_buff(channel, duration=mod.channel_turns)
                    break
        else:
            yield from self._shape_cast(actual_x, actual_y)

    def _shape_cast(self, x: int, y: int) -> Generator[None, None, None]:
        """Delegate to the shape handler's cast() generator."""
        yield from self._shape_handler.cast(self, x, y)

    def get_impacted_tiles(self, x: int, y: int) -> list[Point]:
        """Delegate to shape handler."""
        if self._shape_handler and hasattr(self._shape_handler, 'get_impacted_tiles'):
            return self._shape_handler.get_impacted_tiles(self, x, y)
        return [Point(x, y)]

    # -------------------------------------------------------------------
    # Callbacks used by shape handlers during cast
    # -------------------------------------------------------------------
    def _apply_element_secondary(self, x: int, y: int) -> None:
        """Apply element secondary effect at a hit point."""
        if self._element_handler and hasattr(self._element_handler, 'apply_secondary'):
            self._element_handler.apply_secondary(self, self.level, x, y)

    def _apply_modifier_effects(self, x: int, y: int) -> None:
        """Apply modifier post-hit effects at a hit point."""
        for mod, handler in zip(self._modifiers, self._modifier_handlers):
            if handler and hasattr(handler, 'apply_effect'):
                handler.apply_effect(self, self.level, x, y)

    # -------------------------------------------------------------------
    # Stat override for piercing modifier
    # -------------------------------------------------------------------
    def get_stat(self, attr: str, base: int | None = None) -> int:
        """Override to apply modifier stat adjustments."""
        value = super().get_stat(attr, base)

        # Apply modifier stat modifications via handlers
        if attr == "damage":
            stats = {"damage": value}
            for handler in self._modifier_handlers:
                if hasattr(handler, 'modify_stats'):
                    stats = handler.modify_stats(self, stats)
            return stats.get("damage", value)

        if attr == "range":
            stats = {"range": value}
            for handler in self._modifier_handlers:
                if hasattr(handler, 'modify_stats'):
                    stats = handler.modify_stats(self, stats)
            return stats.get("range", value)

        return value

    # -------------------------------------------------------------------
    # AI targeting
    # -------------------------------------------------------------------
    def get_ai_target(self) -> Point | None:
        """AI targeting — use homing retargeting if available."""
        target = super().get_ai_target()

        if target is not None:
            for mod, handler in zip(self._modifiers, self._modifier_handlers):
                if mod.homing and hasattr(handler, 'retarget'):
                    return handler.retarget(self, target.x, target.y)

        return target

    def can_cast(self, x: int, y: int) -> bool:
        """Override for Self-cast spells that always target the caster."""
        if self._shape.name == "Self" and self.caster:
            return x == self.caster.x and y == self.caster.y
        if self._shape.name == "Cone" and self.caster:
            # Cone targets a direction, not a specific tile
            return self.caster is not None and self.level is not None
        return super().can_cast(x, y)

    def __repr__(self) -> str:
        mods = f" +{'+'.join(m.name for m in self._modifiers)}" if self._modifiers else ""
        return f"<{self.name}{mods} (d={self.damage} r={self.range})>"
