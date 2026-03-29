"""Spell crafting component definitions: Element, Shape, Modifier.

A spell = Element + Shape + 0-2 Modifiers.
Components are purchased once with SP; crafting from owned components is free.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from game.constants import Tag, Tags

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Element — damage type + secondary effect behavior
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Element:
    """An element determines the damage type and secondary effects of a spell."""
    name: str
    tag: Tag
    base_damage: int
    tier: int               # 1-3
    sp_cost: int
    description: str = ""
    # Secondary effect params (used by element handler)
    dot_damage: int = 0     # Damage-over-time per turn
    dot_duration: int = 0   # DOT turns
    secondary_effect: str = ""  # Handler key for special effects


@dataclass(frozen=True)
class Shape:
    """A shape determines how the spell is delivered (bolt, burst, etc.)."""
    name: str
    tag: Tag                # Pseudo-tag for shape upgrades (Tags.Shape_Bolt, etc.)
    base_range: int
    base_radius: int
    base_charges: int
    tier: int
    sp_cost: int
    requires_los: bool = True
    can_target_self: bool = False
    can_target_empty: bool = True
    melee: bool = False
    description: str = ""


@dataclass(frozen=True)
class Modifier:
    """A modifier enhances a crafted spell (0-2 per spell)."""
    name: str
    tier: int
    sp_cost: int
    description: str = ""
    # Stat modifications
    damage_mult: float = 1.0        # Multiplier on base damage
    range_bonus: int = 0
    radius_bonus: int = 0
    charges_bonus: int = 0
    # Special behaviors (interpreted by modifier handlers)
    dot_turns: int = 0              # Lingering: extra DOT duration
    chain_targets: int = 0          # Splitting: chain to N extra targets
    channel_turns: int = 0          # Channeled: multi-turn sustained cast
    pierce_pct: int = 0             # Piercing: resistance bypass percentage
    volatile_radius: int = 0        # Volatile: secondary explosion radius
    homing: bool = False            # Homing: auto-correct trajectory
    # Incompatibilities
    incompatible_with: frozenset[str] = field(default_factory=frozenset)


# ===========================================================================
# ELEMENT REGISTRY
# ===========================================================================
ELEMENTS: dict[str, Element] = {}

def _reg_element(e: Element) -> Element:
    ELEMENTS[e.name] = e
    return e

FIRE = _reg_element(Element(
    name="Fire", tag=Tags.Fire, base_damage=9, tier=1, sp_cost=1,
    description="Burns enemies, dealing damage over time.",
    dot_damage=2, dot_duration=3, secondary_effect="burn",
))
ICE = _reg_element(Element(
    name="Ice", tag=Tags.Ice, base_damage=7, tier=1, sp_cost=1,
    description="Freezes enemies, slowing their movement.",
    secondary_effect="freeze",
))
LIGHTNING = _reg_element(Element(
    name="Lightning", tag=Tags.Lightning, base_damage=11, tier=1, sp_cost=1,
    description="Shocks enemies. Chains to nearby targets.",
    secondary_effect="shock",
))
DARK = _reg_element(Element(
    name="Dark", tag=Tags.Dark, base_damage=8, tier=2, sp_cost=2,
    description="Drains life from enemies.",
    secondary_effect="lifedrain",
))
HOLY = _reg_element(Element(
    name="Holy", tag=Tags.Holy, base_damage=8, tier=2, sp_cost=2,
    description="Deals bonus damage to undead and demons.",
    secondary_effect="smite",
))
NATURE = _reg_element(Element(
    name="Nature", tag=Tags.Nature, base_damage=6, tier=1, sp_cost=1,
    description="Poisons enemies with toxic thorns.",
    dot_damage=3, dot_duration=4, secondary_effect="poison",
))
ARCANE = _reg_element(Element(
    name="Arcane", tag=Tags.Arcane, base_damage=12, tier=3, sp_cost=3,
    description="Pure magical energy. Ignores a portion of resistance.",
    secondary_effect="arcane_pierce",
))
POISON = _reg_element(Element(
    name="Poison", tag=Tags.Poison, base_damage=4, tier=1, sp_cost=1,
    description="Weak initial hit but strong damage over time.",
    dot_damage=4, dot_duration=5, secondary_effect="envenom",
))


# ===========================================================================
# SHAPE REGISTRY
# ===========================================================================
SHAPES: dict[str, Shape] = {}

def _reg_shape(s: Shape) -> Shape:
    SHAPES[s.name] = s
    return s

BOLT = _reg_shape(Shape(
    name="Bolt", tag=Tags.Shape_Bolt,
    base_range=7, base_radius=0, base_charges=8, tier=1, sp_cost=1,
    description="A projectile that travels in a line. Stops at first target hit.",
))
BURST = _reg_shape(Shape(
    name="Burst", tag=Tags.Shape_Burst,
    base_range=6, base_radius=2, base_charges=5, tier=1, sp_cost=1,
    description="An explosion at the target point. Hits all units in radius.",
))
BEAM = _reg_shape(Shape(
    name="Beam", tag=Tags.Shape_Beam,
    base_range=8, base_radius=0, base_charges=6, tier=2, sp_cost=2,
    description="A piercing ray that passes through all units in a line.",
))
CONE = _reg_shape(Shape(
    name="Cone", tag=Tags.Shape_Cone,
    base_range=0, base_radius=4, base_charges=3, tier=2, sp_cost=2,
    can_target_self=True,
    description="A cone of energy emanating from the caster toward the target direction.",
))
ORB = _reg_shape(Shape(
    name="Orb", tag=Tags.Shape_Orb,
    base_range=9, base_radius=0, base_charges=2, tier=2, sp_cost=2,
    description="A slow-moving orb that damages everything in its path. Persists for several turns.",
))
TOUCH = _reg_shape(Shape(
    name="Touch", tag=Tags.Shape_Touch,
    base_range=1, base_radius=0, base_charges=12, tier=1, sp_cost=1,
    melee=True,
    description="A melee-range spell. High charges, must be adjacent to target.",
))
SELF = _reg_shape(Shape(
    name="Self", tag=Tags.Shape_Self,
    base_range=0, base_radius=0, base_charges=2, tier=1, sp_cost=1,
    can_target_self=True, can_target_empty=True,
    description="Cast on yourself. Applies an aura or self-buff.",
))
SUMMON = _reg_shape(Shape(
    name="Summon", tag=Tags.Shape_Summon,
    base_range=4, base_radius=0, base_charges=2, tier=2, sp_cost=2,
    description="Summons an elemental minion at the target location.",
))


# ===========================================================================
# MODIFIER REGISTRY
# ===========================================================================
MODIFIERS: dict[str, Modifier] = {}

def _reg_modifier(m: Modifier) -> Modifier:
    MODIFIERS[m.name] = m
    return m

EMPOWERED = _reg_modifier(Modifier(
    name="Empowered", tier=1, sp_cost=1,
    description="Increases spell damage by 50%.",
    damage_mult=1.5,
))
EXTENDED = _reg_modifier(Modifier(
    name="Extended", tier=1, sp_cost=1,
    description="Increases spell range by 3.",
    range_bonus=3,
    incompatible_with=frozenset({"Self"}),  # Self-cast has no range
))
LINGERING = _reg_modifier(Modifier(
    name="Lingering", tier=2, sp_cost=2,
    description="Creates a persistent zone that damages enemies for 3 turns.",
    dot_turns=3,
    incompatible_with=frozenset({"Self", "Summon"}),
))
SPLITTING = _reg_modifier(Modifier(
    name="Splitting", tier=2, sp_cost=2,
    description="Spell chains to 2 additional nearby targets.",
    chain_targets=2,
    incompatible_with=frozenset({"Self", "Burst", "Cone"}),  # AOE already hits multiple
))
CHANNELED = _reg_modifier(Modifier(
    name="Channeled", tier=2, sp_cost=2,
    description="Sustain the spell for 3 turns, re-applying each turn.",
    channel_turns=3,
    incompatible_with=frozenset({"Touch"}),
))
HOMING = _reg_modifier(Modifier(
    name="Homing", tier=1, sp_cost=1,
    description="Spell seeks the nearest enemy. Never misses.",
    homing=True,
    incompatible_with=frozenset({"Self", "Burst", "Cone", "Touch"}),
))
PIERCING = _reg_modifier(Modifier(
    name="Piercing", tier=2, sp_cost=2,
    description="Ignores 50% of target's resistance.",
    pierce_pct=50,
))
VOLATILE = _reg_modifier(Modifier(
    name="Volatile", tier=2, sp_cost=2,
    description="Target explodes on death, dealing area damage in radius 2.",
    volatile_radius=2,
    incompatible_with=frozenset({"Self"}),
))
